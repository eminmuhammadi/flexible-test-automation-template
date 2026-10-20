import allure
import pytest
from playwright.sync_api import Page, expect

from pages.browser.shop.login_page import LoginPage


@pytest.mark.browser
@pytest.mark.shop
@pytest.mark.regression
@allure.epic("QA Automation Platform")
@allure.feature("Browser")
@allure.story("Shopping cart")
class TestCart:
    @allure.title("{product_name} can be added to the cart")
    @pytest.mark.parametrize(
        ("product", "product_name"),
        [
            pytest.param(
                "backpack", "Sauce Labs Backpack",
                marks=[pytest.mark.smoke, pytest.mark.test_case(id="TEST-04")],
                id="TEST-04",
            ),
            pytest.param(
                "bike-light", "Sauce Labs Bike Light",
                marks=pytest.mark.test_case(id="TEST-05"),
                id="TEST-05",
            ),
            pytest.param(
                "bolt-t-shirt", "Sauce Labs Bolt T-Shirt",
                marks=pytest.mark.test_case(id="TEST-06"),
                id="TEST-06",
            ),
        ],
        ids=("backpack", "bike-light", "bolt-t-shirt"),
    )
    def test_standard_user_can_add_product_to_cart(
        self, page: Page, product: str, product_name: str
    ) -> None:
        with allure.step("Sign in to the shop"):
            login_page = LoginPage(page)
            login_page.open()
            inventory_page = login_page.login()

        with allure.step(f"Add {product_name} and verify the cart"):
            expect(inventory_page.title).to_have_text("Products")
            inventory_page.add_product_to_cart(product)
            cart_page = inventory_page.open_cart()
            expect(cart_page.first_item_name).to_have_text(product_name)
