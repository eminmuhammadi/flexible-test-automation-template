import hashlib
import os
import re
from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from appium import webdriver
from playwright.sync_api import (
    APIRequestContext,
    BrowserContext,
    Playwright,
    sync_playwright,
)
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings
from mobile.options import build_mobile_options


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    args = config.invocation_params.args
    for env_name, option, allowed in (
        ("PLAYWRIGHT_BROWSER", "browser", {"chromium", "firefox", "webkit"}),
        ("PLAYWRIGHT_HEADED", "headed", {"on", "off"}),
        ("PLAYWRIGHT_TRACING", "tracing", {"on", "off", "retain-on-failure"}),
        ("PLAYWRIGHT_VIDEO", "video", {"on", "off", "retain-on-failure"}),
    ):
        value = os.getenv(env_name, "").strip().lower()
        if not value:
            continue
        if value not in allowed:
            raise pytest.UsageError(f"Invalid {env_name}: {value!r}")
        if not any(
            arg == f"--{option}" or arg.startswith(f"--{option}=") for arg in args
        ):
            if option == "headed":
                config.option.headed = value == "on"
            else:
                setattr(config.option, option, [value] if option == "browser" else value)


@pytest.fixture(scope="session")
def device(playwright: Playwright, pytestconfig: pytest.Config) -> str | None:
    cli_device = pytestconfig.getoption("--device")
    if cli_device:
        return cli_device

    profile = os.getenv("BROWSER_PROFILE", "desktop").strip()
    profiles = {
        "desktop": None,
        "mobile": "Pixel 7",
        "iphone": "iPhone 13",
        "ipad": "iPad (gen 5)",
    }
    selected = profiles.get(profile.lower(), profile)
    if selected and selected not in playwright.devices:
        raise pytest.UsageError(
            f"Unknown BROWSER_PROFILE {profile!r}; use desktop, mobile, iphone, ipad, "
            "or a Playwright device name"
        )
    return selected


@pytest.fixture
def context(
    new_context: Callable[..., BrowserContext], request: pytest.FixtureRequest
) -> BrowserContext:
    record_har = os.getenv("PLAYWRIGHT_HAR", "off").strip().lower()
    if record_har not in {"on", "off"}:
        raise pytest.UsageError("PLAYWRIGHT_HAR must be on or off")
    if record_har == "off":
        return new_context()

    output_dir = Path(os.getenv("PLAYWRIGHT_HAR_DIR", "reports/playwright/har"))
    output_dir.mkdir(parents=True, exist_ok=True)
    node_id = request.node.nodeid
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", request.node.name).strip("_.-")[:120]
    suffix = hashlib.sha1(node_id.encode()).hexdigest()[:8]
    return new_context(record_har_path=output_dir / f"{name}-{suffix}.har")


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.from_env()


@pytest.fixture
def api_request_context(
    settings: Settings,
) -> Generator[APIRequestContext, None, None]:
    with sync_playwright() as playwright:
        request = playwright.request.new_context(
            base_url=settings.api_base_url,
            extra_http_headers={"Accept": "application/json"},
        )
        yield request
        request.dispose()


@pytest.fixture
def mobile_driver(settings: Settings) -> Generator[WebDriver, None, None]:
    try:
        options = build_mobile_options(settings)
    except ValueError as error:
        raise pytest.UsageError(str(error)) from error

    driver = webdriver.Remote(settings.appium_server_url, options=options)
    try:
        yield driver
    finally:
        driver.quit()
