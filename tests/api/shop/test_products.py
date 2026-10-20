import allure
import pytest
from playwright.sync_api import APIRequestContext

from domains.api.shop.products_page import ProductsPage


@pytest.mark.api
@pytest.mark.shop
@pytest.mark.regression
@allure.epic("Saucedemo Shop")
@allure.story("As a user, I want to see products data")
class TestProducts:
    @allure.title("Product {product_id} should cost {expected_price}")
    @pytest.mark.parametrize(
        ("product_id", "expected_price"),
        [
            pytest.param(
                1,
                109.95,
                marks=pytest.mark.test_case(id="TEST-01"),
            ),
            pytest.param(
                2,
                22.30,
                marks=pytest.mark.test_case(id="TEST-02"),
            ),
            pytest.param(
                3,
                55.99,
                marks=pytest.mark.test_case(id="TEST-03"),
            ),
        ],
    )
    def test_product_details_are_returned(
        self,
        api_request_context: APIRequestContext,
        product_id: int,
        expected_price: float,
    ) -> None:
        products_page = ProductsPage(api_request_context)
        with allure.step(f"Request product {product_id}"):
            response = products_page.get_product(product_id)
            allure.attach(
                f"GET /products/{product_id}\nHTTP {response.status}",
                name="API response summary",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step(f"Verify product {product_id} costs {expected_price}"):
            assert response.status == 200
            product = response.json()
            assert product["id"] == product_id
            assert product["title"]
            assert product["price"] == pytest.approx(expected_price)
