from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions

from config.settings import Settings


def build_mobile_options(settings: Settings) -> UiAutomator2Options | XCUITestOptions:
    if not settings.mobile_app_path:
        raise ValueError("MOBILE_APP_PATH must point to the My Demo App build")

    platform = settings.mobile_platform.casefold()
    if platform == "android":
        capabilities = {
            "platformName": "Android",
            "automationName": "UiAutomator2",
            "deviceName": settings.mobile_device_name,
            "app": settings.mobile_app_path,
            **({"udid": settings.mobile_udid} if settings.mobile_udid else {}),
            **(
                {"appWaitActivity": settings.mobile_app_wait_activity}
                if settings.mobile_app_wait_activity
                else {}
            ),
        }
        return UiAutomator2Options().load_capabilities(capabilities)
    if platform == "ios":
        capabilities = {
            "platformName": "iOS",
            "automationName": "XCUITest",
            "deviceName": settings.mobile_device_name,
            "app": settings.mobile_app_path,
            **({"udid": settings.mobile_udid} if settings.mobile_udid else {}),
        }
        return XCUITestOptions().load_capabilities(capabilities)
    raise ValueError("MOBILE_PLATFORM must be Android or iOS")
