import allure
import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import Settings
from pages.mobile.shop.shop_page import ShopPage


@pytest.mark.mobile
@pytest.mark.shop
@pytest.mark.regression
@allure.epic("QA Automation Platform")
@allure.feature("Mobile")
@allure.story("Shopping cart")
class TestShoppingCart:
    @allure.title("My Demo App adds a product to the cart")
    @pytest.mark.test_case(id="TEST-07")
    def test_product_can_be_added_to_cart(
        self, mobile_driver: WebDriver, settings: Settings
    ) -> None:
        shop = ShopPage(mobile_driver, settings.mobile_platform)
        shop.add_product_to_cart()

        assert shop.cart_has_one_item()
