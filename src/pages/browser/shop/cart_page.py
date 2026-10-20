from playwright.sync_api import Locator, Page


class CartPage:
    FIRST_ITEM_NAME_LOCATOR = "[data-test='inventory-item-name']"

    def __init__(self, page: Page) -> None:
        self._page = page

    @property
    def first_item_name(self) -> Locator:
        return self._page.locator(self.FIRST_ITEM_NAME_LOCATOR).first
