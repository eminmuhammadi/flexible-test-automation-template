import allure
import pytest
from playwright.sync_api import APIRequestContext


@pytest.mark.api
@pytest.mark.shop
@pytest.mark.regression
@allure.epic("QA Automation Platform")
@allure.feature("API")
@allure.story("Product details")
class TestProducts:
    @allure.title("Product {product_id} returns the expected details")
    @pytest.mark.parametrize(
        ("product_id", "expected_price"),
        [
            pytest.param(
                1, 109.95,
                marks=pytest.mark.test_case(id="TEST-01"),
                id="TEST-01",
            ),
            pytest.param(
                2, 22.30,
                marks=pytest.mark.test_case(id="TEST-02"),
                id="TEST-02",
            ),
            pytest.param(
                3, 55.99,
                marks=pytest.mark.test_case(id="TEST-03"),
                id="TEST-03",
            ),
        ],
    )
    def test_product_details_are_returned(
        self,
        api_request_context: APIRequestContext,
        product_id: int,
        expected_price: float,
    ) -> None:
        with allure.step(f"Request product {product_id}"):
            response = api_request_context.get(f"/products/{product_id}")

        with allure.step("Verify the product response"):
            assert response.status == 200
            product = response.json()
            assert product["id"] == product_id
            assert product["title"]
            assert product["price"] == pytest.approx(expected_price)
