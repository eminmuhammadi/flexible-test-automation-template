import os

from playwright.sync_api import Page

from pages.browser.shop.inventory_page import InventoryPage


class LoginPage:
    BASE_URL = "https://www.saucedemo.com"
    USERNAME = "standard_user"
    PASSWORD = "secret_sauce"
    USERNAME_LOCATOR = "[data-test='username']"
    PASSWORD_LOCATOR = "[data-test='password']"
    LOGIN_BUTTON_LOCATOR = "[data-test='login-button']"

    def __init__(self, page: Page) -> None:
        self._page = page
        self._base_url = os.getenv("WEB_BASE_URL", self.BASE_URL)
        self._username = os.getenv("WEB_USERNAME", self.USERNAME)
        self._password = os.getenv("WEB_PASSWORD", self.PASSWORD)

    def open(self) -> None:
        self._page.goto(self._base_url)

    def login(
        self, username: str | None = None, password: str | None = None
    ) -> InventoryPage:
        self._page.locator(self.USERNAME_LOCATOR).fill(
            username if username is not None else self._username
        )
        self._page.locator(self.PASSWORD_LOCATOR).fill(
            password if password is not None else self._password
        )
        self._page.locator(self.LOGIN_BUTTON_LOCATOR).click()
        return InventoryPage(self._page)
