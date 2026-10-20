from playwright.sync_api import Locator, Page

from pages.browser.shop.cart_page import CartPage


class InventoryPage:
    TITLE_LOCATOR = "[data-test='title']"
    ADD_TO_CART_LOCATORS = {
        "backpack": "[data-test='add-to-cart-sauce-labs-backpack']",
        "bike-light": "[data-test='add-to-cart-sauce-labs-bike-light']",
        "bolt-t-shirt": "[data-test='add-to-cart-sauce-labs-bolt-t-shirt']",
    }
    CART_LINK_LOCATOR = "[data-test='shopping-cart-link']"

    def __init__(self, page: Page) -> None:
        self._page = page

    @property
    def title(self) -> Locator:
        return self._page.locator(self.TITLE_LOCATOR)

    def add_product_to_cart(self, product: str) -> None:
        self._page.locator(self.ADD_TO_CART_LOCATORS[product]).click()

    def open_cart(self) -> CartPage:
        self._page.locator(self.CART_LINK_LOCATOR).click()
        return CartPage(self._page)
