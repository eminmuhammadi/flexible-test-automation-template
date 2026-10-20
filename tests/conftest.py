import allure
import pytest

pytest_plugins = ["platform_plugin"]


@pytest.fixture(autouse=True)
def allure_test_case_id(request: pytest.FixtureRequest) -> None:
    marker = request.node.get_closest_marker("test_case")
    if marker and (case_id := marker.kwargs.get("id")):
        allure.dynamic.id(case_id)
        allure.dynamic.tag(case_id)
