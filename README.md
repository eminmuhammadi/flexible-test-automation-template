# QA Automation Platform

A compact pytest project for API, browser, Android, and iOS automation. It uses Playwright for both HTTP requests and browser automation, and Appium for native mobile apps. Test cases are pytest methods grouped in suites; page classes own UI locators and actions.

The full implementation-aligned architecture, execution, configuration, development, and operations guide is in [docs/README.md](docs/README.md).

## Project layout

```text
src/
├── pages/                         # UI page objects grouped by platform/domain
│   ├── browser/shop/
│   └── mobile/shop/                # Sauce Labs My Demo App
└── platform/                      # Shared test setup
    ├── config/settings.py         # Environment-backed settings
    ├── mobile/options.py          # Appium capabilities
    ├── platform_plugin.py         # Shared fixtures, configuration, plugin registration
    └── reporting_plugin.py        # Allure metadata and failure screenshots
tests/
├── api/shop/
├── browser/shop/
└── mobile/shop/
```

`tests/conftest.py` loads `platform_plugin`; that plugin registers `reporting_plugin`. Change shared fixtures and lifecycle settings in `src/platform/platform_plugin.py`, and Allure metadata, labels, and failure attachments in `src/platform/reporting_plugin.py`. Test folders can override fixtures in their own `conftest.py` files using normal pytest rules.

API tests use Playwright's `APIRequestContext`. Browser and mobile tests use page objects under `src/pages/<platform>/<domain>/`. Tests live under `tests/<platform>/<domain>/` and carry pytest markers and `TEST-01`, `TEST-02`, … case IDs.

## Install and configure

Requirements: Python 3.12 or newer. Node.js/npm is required to run the pinned Allure CLI (`allure` 3.21.0), but this project does not declare a minimum Node.js version. Running Appium locally also requires Node.js/npm and Appium; tests connecting to a ready remote Appium server do not need those locally. iOS runs require macOS/Xcode on the Appium host, which may be separate from the pytest runner.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
set -a && source .env && set +a
```

Node.js/npm is needed to run the Allure CLI. The project pins CLI version 3.21.0 but does not declare a minimum Node.js version:

```sh
npm ci
python -m pytest tests/api/shop -m api --alluredir=reports/api/allure-results --clean-alluredir
python -m pytest tests/browser/shop -m browser --alluredir=reports/browser/allure-results --clean-alluredir
python -m pytest tests/mobile/shop -m mobile --alluredir=reports/mobile/allure-results --clean-alluredir
npx allure generate reports/*/allure-results --output reports/allure-report --clean
npx allure open reports/allure-report
```

The generated report is a single HTML file with interactive test summaries and charts. API, browser, and mobile results are kept in separate directories and merged into the same report. The mobile test appears under the **Mobile** feature with its Appium steps and `TEST-07` case ID. Direct pytest runs write Allure results to `reports/allure-results/` and Playwright artifacts to `reports/playwright/` by default. The example commands use separate result directories because the default pytest configuration clears `reports/allure-results/` at the start of each run.

The tests read environment variables; they do not load `.env` themselves. `.env.example` selects the Android `Pixel_8_Pro_API_35` AVD. Start that AVD before running mobile checks. Appium must inherit the Android SDK environment (`ANDROID_HOME` or `ANDROID_SDK_ROOT`).

## Allure reporting

Run a case and generate its HTML report in one command, then open it locally:

```sh
npm run test:report -- TEST-07
npm run report:open
```

Use `all` instead of a case ID to run the full suite; extra pytest arguments work as usual, for example `npm run test:report -- all -m api`. Allure builds the report even when tests fail and preserves the failing exit status. This command reports only results written by that run. To combine existing results from direct pytest runs and tagged runs, use `npm run report`.

For a live view, start the watcher and run tests in another terminal:

```sh
npm run report:watch
# In another terminal:
./run_tests.sh all
```

Open the local address printed by the watcher. It discovers new result directories and refreshes as tests finish. The live report is stored in `reports/allure-live/`; it does not overwrite the static report or append partial runs to history. Both viewing commands bind to `127.0.0.1`.

Test titles identify the product and browser or mobile platform. Reports include API, Browser, and Mobile features, mobile platform/device parameters, runtime versions, API status summaries, and screenshots for browser/mobile failures during setup or test execution when a driver is available. Screenshot capture errors appear as diagnostic attachments and preserve the original failure. Full API bodies, credentials, and environment variables are not automatically copied into report metadata; screenshots and existing pytest output can still contain sensitive test data.

Allure configuration sets the history path to `reports/allure-history.jsonl` and the history limit to 30. This is local CLI configuration; the current GitLab pipeline does not generate a combined Allure report or preserve this history.

## Lint

Ruff checks Python style, common errors, and import order. Run it before committing:

```sh
python -m ruff check src tests
```

The repository has no dedicated reporting test suite. The GitLab YAML defines a Ruff lint job, but does not define a reporting regression job.

## Run tests

Use `run_tests.sh` with a pytest case tag to run that case, or `all` to run everything. Extra pytest options are supported:

```sh
./run_tests.sh TEST-01
./run_tests.sh TEST-04 --headed
./run_tests.sh TEST-07
npx allure generate reports/test-*/allure-results --output reports/allure-report --clean
./run_tests.sh all
npx allure generate reports/all/allure-results --output reports/allure-report --clean
```

The script loads `.env` automatically when present. Copy `.env.example` to `.env` and set a valid `MOBILE_APP_PATH` before running `TEST-07`. The mobile fixture checks Appium only when a mobile test runs, whether invoked through the script or directly with pytest. It reuses a ready server or starts a local one, writes its output to `reports/appium.log`, and stops only the process it started. Remote Appium servers must already be running. Tagged results are written under `reports/<tag>/allure-results`; an `all` run writes to `reports/all/allure-results`. Use pytest options such as `-m api`, `-m mobile`, or `-k <expression>` to filter tests; repeated `-m` expressions in the script are combined with the case tag.

Browser actions run without an added delay by default. Pass `--slowmo=1000` when you want a visible one-second pause per action. Select a single case with `-m "test_case(id='TEST-01')"`; use `-m api` for API cases or `-m regression` for regression cases.

## Add a browser or mobile test

Record the user flow and useful locators, then fit them into the existing pytest and page-object structure. Generated code is a starting point; keep the project's fixtures and test conventions.

### Browser: Playwright Codegen

With the virtual environment active and `.env` loaded, record against the configured site:

```sh
playwright codegen --target=python-pytest "$WEB_BASE_URL"
```

Use the browser window to perform the flow. In Playwright Inspector, add assertions or pick locators, then copy the generated Python. See the [Playwright Codegen guide](https://playwright.dev/python/docs/codegen).

Create the test under `tests/browser/<domain>/test_<flow>.py`. Use the existing `page` fixture and move reusable locators and actions into `src/pages/browser/<domain>/`. Keep outcome assertions in the test with Playwright `expect`, following `tests/browser/shop/test_cart.py` and the `src/pages/browser/shop/` page objects. Replace any captured credentials with the environment-backed settings; do not commit real passwords or session data.

### Native mobile: Appium Inspector Recorder

Start the Appium server and target emulator/device using the setup in [Mobile My Demo App checks](#mobile-my-demo-app-checks). In Appium Inspector, set the server URL from `APPIUM_SERVER_URL`, add capabilities for the same platform, device, and app, then start a session. For the Android values in `.env.example`, the capabilities are:

```json
{
  "platformName": "Android",
  "appium:automationName": "UiAutomator2",
  "appium:deviceName": "Pixel_8_Pro_API_35",
  "appium:app": "https://github.com/saucelabs/my-demo-app-android/releases/download/2.3.0/mda-2.3.0-27.apk",
  "appium:appWaitActivity": "com.saucelabs.mydemoapp.android.view.activities.MainActivity"
}
```

In the Inspector toolbar, enable recording, choose the Python client, perform the flow, and copy the generated code from the Recorder tab. See the [Appium Inspector Recorder guide](https://appium.github.io/appium-inspector/latest/session-inspector/recorder/).

Create the test under `tests/mobile/<domain>/test_<flow>.py` and put reusable locators and actions in `src/pages/mobile/<domain>/`. Use the existing `mobile_driver` fixture instead of the recorder's session-creation boilerplate, and use explicit waits and a final assertion. Follow `tests/mobile/shop/test_my_demo_app_cart.py` and `src/pages/mobile/shop/shop_page.py`; provide platform-specific locators when Android and iOS differ.

### Identify and run the case

Add the appropriate platform/domain markers and a unique `@pytest.mark.test_case(id="TEST-XX")` marker. `run_tests.sh` selects tests through this marker. For parametrized tests, put a distinct marker on each `pytest.param`; its separate `id=` argument is optional because pytest generates a display ID automatically.

```sh
./run_tests.sh TEST-08 --headed  # Browser example
./run_tests.sh TEST-09           # Mobile example
```

## Mobile My Demo App checks

Install Appium and the driver for the platform. The mobile fixture starts a local Appium server when a selected mobile test needs it:

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

The sample adds a catalog product to the cart and verifies the cart count. `MOBILE_APP_PATH` in `.env.example` points to the Sauce Labs Android APK. The test passes this value to Appium as the `app` capability; use a build URL the Appium host can retrieve or a local `.apk`/`.ipa` path visible to that host.

For an iOS simulator, run Appium on macOS with Xcode and select the simulator build in `.env`:

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
| `MOBILE_APP_PATH` | Sauce Labs Android 2.3.0 APK URL | Appium `app` capability; local files must be visible to the Appium host and URLs retrievable by it; select an iOS build for iOS runs |
| `MOBILE_APP_WAIT_ACTIVITY` | unset | Optional Android activity to wait for when startup redirects from the manifest launch activity |

Browser profiles use Playwright device descriptors. For iPad Safari emulation, run `BROWSER_PROFILE=ipad PLAYWRIGHT_BROWSER=webkit python -m pytest -m browser`. Recording files can contain page content, cookies, headers, and request data; protect CI artifacts and use test accounts only.

The `PLAYWRIGHT_BROWSER`, `PLAYWRIGHT_HEADED`, `PLAYWRIGHT_TRACING`, and `PLAYWRIGHT_VIDEO` environment variables supply defaults. Explicit pytest arguments, `PYTEST_ADDOPTS`, and pytest configuration take precedence. Multiple `--browser` options select multiple engines. Use `--tracing=retain-on-failure --output=reports/playwright` to keep traces for failing browser or API tests; inspect a retained `trace.zip` with `python -m playwright show-trace <path-to-trace.zip>`.

Set `PLAYWRIGHT_HEADED=on` in `.env` to see the browser while tests run, or use `PLAYWRIGHT_HEADED=off` for headless runs. The Playwright `--headed` command-line option overrides the environment setting.

## GitLab CI

The YAML declares stages `lint`, `api`, `browser`, `ios`, and `android`, but API/browser jobs use `stage: test` and mobile jobs use `stage: mobile`; those names are not declared. GitLab normally rejects undeclared job stages, so validate or correct this mismatch before relying on the pipeline. The API and browser jobs request JUnit, HTML, and Playwright artifacts; Android and iOS jobs are gated by `RUN_ANDROID=true` and `RUN_IOS=true` and use `android` and `macos` runner tags. No Allure aggregation job is present. The mobile jobs install Python requirements only: runner hosts must provide Appium, the platform driver, SDK/Xcode, and device infrastructure. The iOS CI app URL points to an `.ipa`, which is not the simulator build.
