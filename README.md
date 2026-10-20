# QA Automation Platform

A compact pytest project for API, browser, Android, and iOS automation. It uses Playwright for both HTTP requests and browser automation, and Appium for native mobile apps. Test cases are pytest methods grouped in suites; page classes own UI locators and actions.

## Project layout

```text
src/
├── pages/                         # UI page objects grouped by platform/domain
│   ├── browser/shop/
│   └── mobile/shop/                # Sauce Labs My Demo App
└── platform/                      # Shared test setup
    ├── config/settings.py         # Environment-backed settings
    ├── mobile/options.py          # Appium capabilities
    └── platform_plugin.py        # pytest fixtures and Playwright configuration
tests/
├── api/shop/
├── browser/shop/
└── mobile/shop/
```

API tests use Playwright's `APIRequestContext`. Browser and mobile tests use page objects under `src/pages/<platform>/<domain>/`. Tests live under `tests/<platform>/<domain>/` and carry pytest markers and `TEST-01`, `TEST-02`, … case IDs.

## Install and configure

Requirements: Python 3.12 or newer. Mobile runs also need Node.js, Appium, and an Android emulator/device or a macOS iOS device runner with Xcode.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
set -a && source .env && set +a
```

Node.js 22 or newer is needed to build and view the Allure report. The report CLI is pinned in `package-lock.json`:

```sh
npm ci
python -m pytest tests/api/shop -m api --alluredir=reports/api/allure-results --clean-alluredir
python -m pytest tests/browser/shop -m browser --alluredir=reports/browser/allure-results --clean-alluredir
python -m pytest tests/mobile/shop -m mobile --alluredir=reports/mobile/allure-results --clean-alluredir
npx allure generate reports/*/allure-results --output reports/allure-report --clean
npx allure open reports/allure-report
```

The generated report is a single HTML file with interactive test summaries and charts. API, browser, and mobile results are kept in separate directories and merged into the same report. The mobile test appears under the **Mobile** feature with its Appium steps and `TEST-07` case ID. The example commands use separate result directories because the default pytest configuration clears `allure-results/` at the start of each run.

The tests read environment variables; they do not load `.env` themselves. `.env.example` selects the Android `Pixel_8_Pro_API_35` AVD. Start that AVD and the Appium server before running mobile checks. Appium must inherit the Android SDK environment (`ANDROID_HOME` or `ANDROID_SDK_ROOT`).

## Lint

Ruff checks Python style, common errors, and import order. Run it before committing:

```sh
python -m ruff check src tests
```

The same check runs as a separate GitLab CI job.

## Run tests

Use `run_tests.sh` with a pytest case tag to run that case, or `all` to run everything. Extra pytest options are supported:

```sh
./run_tests.sh TEST-01
./run_tests.sh TEST-04 --headed
./run_tests.sh TEST-07
npx allure generate reports/test-*/allure-results --output reports/allure-report --clean
./run_tests.sh all --slowmo=0
npx allure generate reports/all/allure-results --output reports/allure-report --clean
```

The script loads `.env` automatically when present. Copy `.env.example` to `.env` and set a valid `MOBILE_APP_PATH` before running `TEST-07`. When selected tests include the `mobile` marker, it reuses Appium if available or starts the locally configured server and stops only the process it started. Remote Appium servers must already be running. Tagged results are written under `reports/<tag>/allure-results`; an `all` run writes to `reports/all/allure-results`. Use pytest options such as `-m smoke`, `-m mobile`, or `-k <expression>` to filter tests.

The default Playwright slow motion is **1,000 ms** per browser action. Override it with `--slowmo=<milliseconds>`, for example `--slowmo=0`. Select a single case with `-m "test_case(id='TEST-01')"`; use `-m smoke` for smoke cases or `-m regression` for regression cases.

## Mobile My Demo App checks

Install Appium and the driver for the platform. The test script starts a local Appium server when a selected mobile test needs it:

```sh
npm install --global appium
appium driver install uiautomator2  # Android
appium driver install xcuitest      # iOS, on macOS with Xcode
appium
```

In another terminal, start the configured Android AVD:

```sh
emulator -avd Pixel_8_Pro_API_35
./run_tests.sh all -m mobile
```

The sample adds a catalog product to the cart and verifies the cart count. `MOBILE_APP_PATH` in `.env.example` points to the Sauce Labs Android APK; Appium downloads and installs it when starting the session. Use a local `.apk`/`.ipa` path instead if preferred.

For an iOS simulator, select the simulator build in `.env`:

```sh
MOBILE_PLATFORM=iOS
MOBILE_DEVICE_NAME="iPhone 16 Pro Max"
MOBILE_APP_PATH=https://github.com/saucelabs/my-demo-app-ios/releases/download/2.3.0/SauceLabs-Demo-App.Simulator.zip
```

The `.Simulator.zip` build is for iOS simulators. For a physical iPhone, use `SauceLabs-Demo-App.ipa` and set `MOBILE_UDID` from Xcode's Devices and Simulators window; the IPA is built for `iPhoneOS` and cannot run in a simulator. The mobile page objects use the app's Android resource IDs and iOS accessibility identifiers.

## Configuration

Copy `.env.example` and change values for your target. The browser page's default target is SauceDemo; its sample account is public test data.

| Setting | Example value | Used for |
| --- | --- | --- |
| `API_BASE_URL` | `https://fakestoreapi.com` | Playwright API request base URL |
| `WEB_BASE_URL` | `https://www.saucedemo.com` | Browser login page |
| `WEB_USERNAME` / `WEB_PASSWORD` | SauceDemo sample account | Browser login page |
| `BROWSER_PROFILE` | `desktop` | Browser profile: `desktop`, `mobile`, `iphone`, `ipad`, or a Playwright device name |
| `PLAYWRIGHT_BROWSER` | `chromium` | Browser engine: `chromium`, `firefox`, or `webkit` |
| `PLAYWRIGHT_HEADED` | `off` | Show the browser window: `on` or `off`; `--headed` on the pytest command line takes precedence |
| `PLAYWRIGHT_TRACING` | `retain-on-failure` | Playwright trace: `on`, `off`, or `retain-on-failure` |
| `PLAYWRIGHT_VIDEO` | `retain-on-failure` | Browser video: `on`, `off`, or `retain-on-failure` |
| `PLAYWRIGHT_HAR` | `off` | Save one network HAR per browser test: `on` or `off` |
| `PLAYWRIGHT_HAR_DIR` | `reports/playwright/har` | HAR output directory |
| `APPIUM_SERVER_URL` | `http://127.0.0.1:4723` | Appium server endpoint |
| `MOBILE_PLATFORM` | `Android` | `Android` or `iOS` |
| `MOBILE_DEVICE_NAME` | `Pixel_8_Pro_API_35` | Android AVD or iOS device name |
| `MOBILE_UDID` | unset | Optional Appium device UDID; required to target a physical iOS device with the supplied IPA |
| `MOBILE_APP_PATH` | Sauce Labs Android 2.3.0 APK URL | Appium app path or download URL; select the iOS IPA URL for iOS runs |
| `MOBILE_APP_WAIT_ACTIVITY` | unset | Optional Android activity to wait for when startup redirects from the manifest launch activity |

Browser profiles use Playwright device descriptors. For iPad Safari emulation, run `BROWSER_PROFILE=ipad PLAYWRIGHT_BROWSER=webkit python -m pytest -m browser`. Recording files can contain page content, cookies, headers, and request data; protect CI artifacts and use test accounts only.

Set `PLAYWRIGHT_HEADED=on` in `.env` to see the browser while tests run, or use `PLAYWRIGHT_HEADED=off` for headless runs. The Playwright `--headed` command-line option overrides the environment setting.

## GitLab CI

The API and browser jobs run by default and publish JUnit, HTML, and Playwright artifacts. A final CI job combines their Allure results, plus any enabled mobile results, into `reports/allure-report/` as a downloadable single-file HTML artifact retained for 30 days. Android and iOS jobs are opt-in with `RUN_ANDROID=true` and `RUN_IOS=true`; configure matching `android` and `macos` runner tags and provide the Appium server and device. iOS requires macOS, Xcode, and a physical device because the supplied IPA is not simulator-compatible. The mobile jobs install the corresponding My Demo App build from its release URL.
