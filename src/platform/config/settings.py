import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    api_base_url: str
    appium_server_url: str
    mobile_platform: str
    mobile_device_name: str
    mobile_udid: str | None
    mobile_app_path: str | None
    mobile_app_wait_activity: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_base_url=os.getenv("API_BASE_URL", "https://fakestoreapi.com"),
            appium_server_url=os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723"),
            mobile_platform=os.getenv("MOBILE_PLATFORM", "Android"),
            mobile_device_name=os.getenv("MOBILE_DEVICE_NAME", "Android Emulator"),
            mobile_udid=os.getenv("MOBILE_UDID") or None,
            mobile_app_path=os.getenv("MOBILE_APP_PATH") or None,
            mobile_app_wait_activity=os.getenv("MOBILE_APP_WAIT_ACTIVITY") or None,
        )
