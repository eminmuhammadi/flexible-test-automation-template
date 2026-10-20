import platform
from collections.abc import Generator
from importlib.metadata import version
from pathlib import Path
from typing import Any

import allure
import pytest

_screenshot_fixtures = pytest.StashKey[dict[str, Any]]()


@pytest.fixture(scope="session", autouse=True)
def allure_environment(pytestconfig: pytest.Config) -> None:
    output = pytestconfig.getoption("allure_report_dir", default=None)
    if not output:
        return
    environment = {
        "Python": platform.python_version(),
        "OS": platform.system(),
        "pytest": version("pytest"),
        "Playwright": version("playwright"),
        "Appium": version("Appium-Python-Client"),
    }
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "environment.properties").write_text(
        "".join(f"{name}={value}\n" for name, value in environment.items()),
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def allure_test_case_id(request: pytest.FixtureRequest) -> None:
    marker = request.node.get_closest_marker("test_case")
    if marker and (case_id := marker.kwargs.get("id")):
        allure.dynamic.id(case_id)
        allure.dynamic.tag(case_id)
    for name, feature in (("api", "API"), ("browser", "Browser"), ("mobile", "Mobile")):
        if request.node.get_closest_marker(name):
            allure.dynamic.feature(feature)
    if request.node.get_closest_marker("mobile"):
        settings = request.getfixturevalue("settings")
        allure.dynamic.parameter("mobile_platform", settings.mobile_platform)
        allure.dynamic.parameter("mobile_device", settings.mobile_device_name)


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(
    fixturedef: pytest.FixtureDef, request: pytest.FixtureRequest
) -> Generator[None, Any, None]:
    outcome = yield
    if fixturedef.argname in {"page", "mobile_driver"} and outcome.excinfo is None:
        resources = request.node.stash.setdefault(_screenshot_fixtures, {})
        resources[fixturedef.argname] = outcome.get_result()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Function) -> Generator[None, Any, None]:
    report = (yield).get_result()
    if report.when == "teardown":
        item.stash.get(_screenshot_fixtures, {}).clear()
        return
    if (
        not item.config.getoption("allure_report_dir", default=None)
        or not report.failed
        or report.when not in {"setup", "call"}
    ):
        return
    resources = item.stash.get(_screenshot_fixtures, {})
    page = resources.get("page", item.funcargs.get("page"))
    driver = resources.get("mobile_driver", item.funcargs.get("mobile_driver"))
    if page is None and driver is None:
        return
    try:
        if page is not None:
            screenshot = page.screenshot(type="png", timeout=5000)
        else:
            client_config = driver.command_executor.client_config
            previous_timeout = client_config.timeout
            try:
                client_config.timeout = 5
                screenshot = driver.get_screenshot_as_png()
            finally:
                client_config.timeout = previous_timeout
        allure.attach(
            screenshot,
            name=f"Failure screenshot ({report.when})",
            attachment_type=allure.attachment_type.PNG,
        )
    except Exception as error:
        # Diagnostics must preserve the original test failure.
        allure.attach(
            f"Screenshot unavailable: {type(error).__name__}",
            name="Screenshot capture error",
            attachment_type=allure.attachment_type.TEXT,
        )
