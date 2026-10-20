import os

from playwright.sync_api import Page

from domains.browser.shop.inventory_page import InventoryPage


class LoginPage:
    BASE_URL = "https://www.saucedemo.com"
    USERNAME_LOCATOR = "[data-test='username']"
    PASSWORD_LOCATOR = "[data-test='password']"
    LOGIN_BUTTON_LOCATOR = "[data-test='login-button']"

    def __init__(self, page: Page) -> None:
        self._page = page

    def open(self) -> None:
        self._page.goto(self.BASE_URL)

    def login(
        self, username: str | None = None, password: str | None = None
    ) -> InventoryPage:
        username = username if username is not None else os.getenv("WEB_USERNAME")
        password = password if password is not None else os.getenv("WEB_PASSWORD")
        if not username or not password:
            raise ValueError(
                "WEB_USERNAME and WEB_PASSWORD must be configured to log in"
            )

        self._page.locator(self.USERNAME_LOCATOR).fill(username)
        self._page.locator(self.PASSWORD_LOCATOR).fill(password)
        self._page.locator(self.LOGIN_BUTTON_LOCATOR).click()
        return InventoryPage(self._page)
