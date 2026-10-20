from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class ShopPage:
    ANDROID_PACKAGE = "com.saucelabs.mydemoapp.android"
    ANDROID_PRODUCT_ID = f"{ANDROID_PACKAGE}:id/productIV"
    ANDROID_ADD_TO_CART_ID = f"{ANDROID_PACKAGE}:id/cartBt"
    ANDROID_CART_COUNT_ID = f"{ANDROID_PACKAGE}:id/itemsTV"
    ANDROID_CART_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "View cart")
    IOS_PRODUCT_ID = (AppiumBy.ACCESSIBILITY_ID, "ProductItem")
    IOS_ADD_TO_CART = (AppiumBy.ACCESSIBILITY_ID, "Add To Cart")
    IOS_CART_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "Cart-tab-item")
    IOS_CART_COUNT = (AppiumBy.ACCESSIBILITY_ID, "1 Items")
    WAIT_SECONDS = 10

    def __init__(self, driver: WebDriver, platform: str) -> None:
        self._driver = driver
        self._platform = platform.casefold()

    def add_product_to_cart(self) -> None:
        if self._platform == "android":
            products = WebDriverWait(self._driver, self.WAIT_SECONDS).until(
                lambda driver: driver.find_elements(AppiumBy.ID, self.ANDROID_PRODUCT_ID)
            )
            products[0].click()
            self._tap((AppiumBy.ID, self.ANDROID_ADD_TO_CART_ID))
            self._tap(self.ANDROID_CART_BUTTON)
            return

        products = WebDriverWait(self._driver, self.WAIT_SECONDS).until(
            lambda driver: driver.find_elements(*self.IOS_PRODUCT_ID)
        )
        products[0].click()
        self._tap(self.IOS_ADD_TO_CART)
        self._tap(self.IOS_CART_BUTTON)

    def cart_has_one_item(self) -> bool:
        locator = (
            (AppiumBy.ID, self.ANDROID_CART_COUNT_ID)
            if self._platform == "android"
            else self.IOS_CART_COUNT
        )
        count = self._wait_for(locator).text.split()[0]
        return count == "1"

    def _tap(self, locator: tuple[str, str]) -> None:
        WebDriverWait(self._driver, self.WAIT_SECONDS).until(
            EC.element_to_be_clickable(locator)
        ).click()

    def _wait_for(self, locator: tuple[str, str]) -> WebElement:
        return WebDriverWait(self._driver, self.WAIT_SECONDS).until(
            EC.visibility_of_element_located(locator)
        )
