# QA Automation Platform

A pytest project for API, browser, and native mobile checks. Playwright handles HTTP requests and browser sessions; Appium handles Android and iOS apps. Reusable request methods and page objects live in `src/domains/`, while `src/platform/` owns fixtures and reporting.

Start here to run the examples. The [technical guide](docs/README.md) covers configuration, mobile setup, reporting, CI, and adding scenarios.

## Get started

Use **Python 3.12** to match the current CI jobs and Ruff target. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env
```

## Configure targets

Set API and browser target URLs in the corresponding domain class:

- **API:** [`ProductsPage.BASE_URL`](src/domains/api/shop/products_page.py) is `https://fakestoreapi.com`.
- **Browser:** [`LoginPage.BASE_URL`](src/domains/browser/shop/login_page.py) is `https://www.saucedemo.com`.

Edit these constants when changing targets, and update response expectations or UI locators to match the application.

Browser execution settings and mobile targets come from `.env` or exported environment variables. Browser login requires `WEB_USERNAME` and `WEB_PASSWORD`; add them to your ignored `.env` file or protected CI variables. No credentials are supplied in `.env.example`.

`run_tests.sh` loads `.env` automatically. Direct pytest commands require you to export the variables first.

## Run a scenario

```sh
# API suite: TEST-01 through TEST-03
./run_tests.sh all -m api

# One browser cart scenario
./run_tests.sh TEST-04

# Browser suite with a visible window
./run_tests.sh all -m browser --headed

# Mobile cart scenario: needs Appium, an app build, and a running device
./run_tests.sh TEST-07
```

`./run_tests.sh all` includes every suite, including mobile. Case IDs select the `test_case` marker; additional pytest arguments such as `-m`, `-k`, `--browser`, and `--slowmo` are passed through. See [execution and selection](docs/README.md#3-execution-lifecycle).

The sample `.env` selects desktop Chromium with a visible window. Install another browser with `python -m playwright install firefox` or `python -m playwright install webkit`, then select it with `--browser firefox` or `--browser webkit`. Browser device profiles emulate a viewport and device settings; native mobile runs use Appium.

## View reports

Node.js/npm is required for the pinned Allure CLI:

```sh
npm ci
npm run test:report -- TEST-04
npm run report:open
```

To build a report from existing results, run `npm run report`. For a live report while checks run in another terminal, use `npm run report:watch`.

The wrapper writes results to `reports/<lowercase-tag>/allure-results/` and clears that directory when the same tag runs again. Direct pytest defaults to `reports/allure-results/`. Static Allure reports go to `reports/allure-report/`; the watcher uses `reports/allure-live/`. See [reporting and troubleshooting](docs/README.md#9-logging-reporting-and-troubleshooting).

## Project structure

```text
src/
├── domains/
│   ├── api/shop/       # API URL and product requests
│   ├── browser/shop/   # SauceDemo page objects
│   └── mobile/shop/    # My Demo App page object
└── platform/          # Pytest configuration, fixtures, and reporting
tests/
├── api/shop/           # Product response assertions
├── browser/shop/       # Browser cart scenarios
└── mobile/shop/        # Native mobile cart scenario
```

Tests express the scenario and expected result. Domain objects hold request paths, locators, and reusable actions. Fixtures create and close API contexts, browser contexts, and Appium sessions. Use the [development guide](docs/README.md#7-test-development-guide) when adding a scenario.

## Native mobile setup

Mobile checks need an available emulator or device, a matching app build, Appium, and the UiAutomator2 or XCUITest driver. The Android example uses the `Pixel_8_Pro_API_35` AVD; start it before running `TEST-07`. iOS needs macOS and Xcode on the Appium host.

The fixture reuses a ready Appium server. It can start a missing local HTTP server and stops only the process it started. A remote server must already be running. Follow [mobile installation](docs/README.md#5-installation-and-environment-setup) for commands and the distinction between simulator builds and device IPAs.

## GitLab CI

The pipeline uses stages `lint`, `test`, and `mobile`. The API matrix currently lists Python **3.12**. Browser jobs run Chromium, Firefox, and WebKit in separate matrix jobs; available runners determine concurrency. Android and iOS are opt-in jobs requiring prepared runners tagged `android` and `macos`.

Configure browser credentials as CI/CD variables. Mobile runners must supply Appium, platform tooling, a device, and matching target variables. Jobs publish individual artifacts for seven days; there is no combined Allure report job. See [CI configuration](docs/README.md#8-integrations-and-cicd) to change the runtime matrix or enable mobile jobs.

Run the configured style checks before committing:

```sh
python -m ruff check src tests
```
