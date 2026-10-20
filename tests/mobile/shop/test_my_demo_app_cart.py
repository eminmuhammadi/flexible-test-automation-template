import allure
import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings
from pages.mobile.shop.shop_page import ShopPage


@pytest.mark.mobile
@pytest.mark.shop
@pytest.mark.regression
@allure.epic("Saucedemo Shop")
@allure.story("As a user, I want to add products to the cart")
class TestShoppingCart:
    @allure.title("Users should be able to add products on mobile")
    @pytest.mark.test_case(id="TEST-07")
    def test_product_can_be_added_to_cart(
        self, mobile_driver: WebDriver, settings: Settings
    ) -> None:
        allure.dynamic.title(
            f"Add a product to the cart on {settings.mobile_platform}"
        )
        shop = ShopPage(mobile_driver, settings.mobile_platform)
        with allure.step(f"Add a catalog product to the cart on {settings.mobile_platform}"):
            shop.add_product_to_cart()

        with allure.step("Verify one item is shown in the cart"):
            assert shop.cart_has_one_item()
