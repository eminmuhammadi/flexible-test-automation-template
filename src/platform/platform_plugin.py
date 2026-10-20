import hashlib
import ipaddress
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import time
from collections.abc import Callable, Generator
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions
from playwright.sync_api import (
    APIRequestContext,
    BrowserContext,
    Playwright,
)
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings
from mobile.options import build_mobile_options

pytest_plugins = ["reporting_plugin"]


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    args = (
        *config.getini("addopts"),
        *shlex.split(os.getenv("PYTEST_ADDOPTS", "")),
        *config.invocation_params.args,
    )
    for env_name, option, allowed in (
        ("PLAYWRIGHT_BROWSER", "browser", {"chromium", "firefox", "webkit"}),
        ("PLAYWRIGHT_HEADED", "headed", {"on", "off"}),
        ("PLAYWRIGHT_TRACING", "tracing", {"on", "off", "retain-on-failure"}),
        ("PLAYWRIGHT_VIDEO", "video", {"on", "off", "retain-on-failure"}),
    ):
        value = os.getenv(env_name, "").strip().lower()
        if not value:
            continue
        if any(arg == f"--{option}" or arg.startswith(f"--{option}=") for arg in args):
            continue
        if value not in allowed:
            raise pytest.UsageError(f"Invalid {env_name}: {value!r}")
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
    playwright: Playwright,
) -> Generator[APIRequestContext, None, None]:
    request = playwright.request.new_context(
        extra_http_headers={"Accept": "application/json"},
    )
    try:
        yield request
    finally:
        request.dispose()


@pytest.fixture(scope="session")
def mobile_options(settings: Settings) -> UiAutomator2Options | XCUITestOptions:
    try:
        return build_mobile_options(settings)
    except ValueError as error:
        raise pytest.UsageError(str(error)) from error


def _appium_status(url: str) -> str:
    try:
        with urlopen(f"{url.rstrip('/')}/status", timeout=2) as response:
            payload = json.load(response)
    except HTTPError:
        return "malformed"
    except (URLError, TimeoutError, OSError):
        return "unreachable"
    except (ValueError, UnicodeError):
        return "malformed"
    if not isinstance(payload, dict) or not isinstance(payload.get("value"), dict):
        return "malformed"
    return "ready" if payload["value"].get("ready") is True else "unready"


@pytest.fixture(scope="session")
def appium_server(
    settings: Settings, mobile_options: UiAutomator2Options | XCUITestOptions
) -> Generator[str, None, None]:
    url = settings.appium_server_url.rstrip("/")
    try:
        parsed = urlsplit(url)
    except ValueError as error:
        raise pytest.UsageError("APPIUM_SERVER_URL is malformed") from error
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise pytest.UsageError("APPIUM_SERVER_URL must be an HTTP(S) URL with a host")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as error:
        raise pytest.UsageError("APPIUM_SERVER_URL has an invalid port") from error

    status = _appium_status(url)
    if status == "ready":
        yield url
        return
    if status != "unreachable":
        raise pytest.UsageError(f"Appium status response is {status} at {parsed.hostname}")

    try:
        local = parsed.hostname.lower() == "localhost" or ipaddress.ip_address(
            parsed.hostname
        ).is_loopback
    except ValueError:
        local = False
    if parsed.scheme != "http" or not local:
        raise pytest.UsageError(f"Appium is unreachable at {parsed.hostname}; start it first")

    executable = shutil.which("appium")
    if executable is None:
        raise pytest.UsageError("Appium is unavailable and the 'appium' command is missing")
    log_path = Path("reports/appium.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    args = [executable, "--address", parsed.hostname, "--port", str(port)]
    if parsed.path.rstrip("/"):
        args.extend(["--base-path", parsed.path.rstrip("/")])
    with log_path.open("w", encoding="utf-8") as log:
        try:
            process = subprocess.Popen(
                args, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
            )
        except OSError as error:
            raise pytest.UsageError(f"Could not start Appium: {error.strerror}") from error
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise pytest.UsageError(
                        f"Appium exited during startup; see {log_path}"
                    )
                status = _appium_status(url)
                if status == "ready":
                    break
                if status != "unreachable":
                    raise pytest.UsageError(
                        f"Appium status response is {status}; see {log_path}"
                    )
                time.sleep(0.5)
            else:
                raise pytest.UsageError(f"Appium did not become ready; see {log_path}")
            yield url
        finally:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=5)
            else:
                process.wait()


@pytest.fixture
def mobile_driver(
    appium_server: str, mobile_options: UiAutomator2Options | XCUITestOptions
) -> Generator[WebDriver, None, None]:
    driver = webdriver.Remote(appium_server, options=mobile_options)
    try:
        yield driver
    finally:
        driver.quit()
