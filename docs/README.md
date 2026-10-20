# QA Automation Platform — Technical Guide

This document is the operational and contributor guide for the repository. It describes the behavior implemented by the current source and configuration. For architecture boundaries, design decisions, quality attributes, and adoption guidance, see the [System Architecture](ARCHITECTURE.md). For the shortest path from checkout to a first run, see the [root README](../README.md).

## 1. System overview

The project is a pytest-based automation harness with three example surfaces:

| Surface | Framework | Current example | Runtime requirements |
|---|---|---|---|
| API | Playwright synchronous APIRequestContext | GET product records from Fake Store API | Python dependencies and network access to the API |
| Browser | Playwright Page and pytest-playwright fixtures | Sign in to SauceDemo and verify cart contents | Python dependencies, installed matching browser binary, network access, and WEB_USERNAME/WEB_PASSWORD |
| Native mobile | Appium Python Client and Selenium WebDriver | Add a product in Sauce Labs My Demo App and verify cart count | Appium server, compatible app build, platform driver, device/simulator, and host tooling |

With one browser engine selected, the repository defines seven cases: TEST-01 through TEST-03 for API data, TEST-04 through TEST-06 for browser cart behavior, and TEST-07 for a mobile cart flow. Selecting several browser engines repeats TEST-04 through TEST-06 for each engine. The target services and app builds are external to this repository.

The execution process is intentionally simple: install dependencies, select scenarios, run pytest, retain the resulting artifacts, and optionally generate an Allure HTML report. The system does not start or provision the API, website, mobile application, browser binaries, or devices.

## 2. Repository map and ownership

    src/
    ├── domains/
    │   ├── api/shop/products_page.py
    │   ├── browser/shop/
    │   │   ├── login_page.py
    │   │   ├── inventory_page.py
    │   │   └── cart_page.py
    │   └── mobile/shop/shop_page.py
    └── platform/
        ├── config/settings.py
        ├── mobile/options.py
        ├── platform_plugin.py
        └── reporting_plugin.py
    tests/
    ├── conftest.py
    ├── api/shop/test_products.py
    ├── browser/shop/test_cart.py
    └── mobile/shop/test_my_demo_app_cart.py

The remaining root-level files provide execution and tool configuration:

| File | Purpose |
|---|---|
| pytest.ini | Import roots, test discovery root, default pytest options, and registered markers |
| requirements.txt | Exact Python dependency pins |
| pyproject.toml | Ruff target version, line length, source roots, and lint/import rules |
| pyrightconfig.json | Static analysis include paths; Pyright itself is not installed or invoked by the pipeline |
| run_tests.sh | Local wrapper for environment loading, case-tag selection, and tag-scoped Allure output |
| .env.example | Credential-free local execution defaults and mobile examples |
| .gitlab-ci.yml | Lint, API, browser, and opt-in mobile jobs |
| package.json and package-lock.json | Pinned Allure CLI dependency and report scripts |
| allurerc.json and allure.watch.mjs | Allure report input/output configuration and live-watch behavior |

Scenario tests should own expected outcomes. Domain objects should own target-specific paths, selectors, and actions. The platform plugin should own shared resource creation and teardown. Avoid creating a second driver or request context inside a test when the corresponding fixture already defines its lifecycle.

Pytest's import paths include src and src/platform. Imports therefore use names such as domains.api.shop.products_page and config.settings. Run commands from the repository root; the shell wrapper changes to that directory automatically, while direct pytest commands should be invoked from it.

## 3. Installation and prerequisites

### 3.1 Python and browser setup

Use Python 3.12, which matches the Ruff target and current CI runtime.

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    python -m playwright install chromium
    cp .env.example .env

For Firefox or WebKit browser checks, install the matching binary:

    python -m playwright install firefox
    python -m playwright install webkit

API tests use Playwright's request client and do not launch a browser, although Playwright remains an installed Python dependency.

The root README gives example commands to configure login credentials and run a case. Browser login requires WEB_USERNAME and WEB_PASSWORD unless credentials are passed explicitly to LoginPage.login(). The supplied .env.example deliberately contains no credentials.

### 3.2 Allure report tooling

Node.js/npm is required for the pinned Allure command-line package:

    npm ci

Install report tooling when you need to generate or serve an HTML report. Pytest can write raw Allure results without an Allure server or report process running.

### 3.3 Mobile host prerequisites

Mobile checks require an Appium host with the corresponding driver and a compatible app build/device pairing.

Android requirements include:

- Appium and the UiAutomator2 driver on the Appium host.
- Android SDK/platform tools and required environment variables on that host.
- A running emulator or connected device.
- An Android APK accessible to the Appium host.
- A device name matching the selected emulator or device.

Example host setup:

    npm install --global appium
    appium driver install uiautomator2
    emulator -avd Pixel_8_Pro_API_35

The emulator command starts an AVD; setting MOBILE_DEVICE_NAME only identifies the device for Appium and does not start it.

iOS requirements include a macOS host with Xcode and the XCUITest driver:

    npm install --global appium
    appium driver install xcuitest

For Simulator execution, use a Simulator-compatible app build and a running simulator. For a physical iOS device, use a compatible signed IPA and provide its UDID where required. The sample/CI IPA targets a physical device and cannot run in Simulator. Signing, device registration, and host provisioning remain responsibilities of the Appium environment.

### 3.4 Appium endpoint modes

The default endpoint is http://127.0.0.1:4723. The mobile fixture first checks the endpoint's /status response and requires value.ready to be true.

If the endpoint is ready, it is reused. If it is unreachable at a plain HTTP loopback address, the fixture may start the local appium executable and stop only the process group it created after the test session. The local server log is written to reports/appium.log. Startup is bounded by a 30-second readiness poll.

Remote or HTTPS Appium endpoints must already be running. An unready or malformed status response is treated as a setup error. A local file path or app URL in MOBILE_APP_PATH must be resolvable from the Appium host, which may differ from the machine running pytest.

## 4. Running and selecting tests

### 4.1 Wrapper commands

Use run_tests.sh for common local workflows:

    # Run the API suite
    ./run_tests.sh all -m api

    # Run one browser cart case
    ./run_tests.sh TEST-04

    # Run the browser suite with a visible browser
    ./run_tests.sh all -m browser --headed

    # Run one mobile case after preparing Appium and a device
    ./run_tests.sh TEST-07

    # Select a case and an additional suite marker
    ./run_tests.sh TEST-04 -m browser

    # Select the API suite and filter test names
    ./run_tests.sh all -m api -k product

    # Select an engine and add a delay between Playwright actions
    ./run_tests.sh TEST-04 --browser chromium --headed --slowmo=500

The first argument is a case tag and defaults to all. A case tag is translated to a test_case marker expression. Case IDs are case-sensitive. The wrapper accepts -m, -mEXPR, --markexpr, and --markexpr=EXPR and combines a supplied marker with the case marker using AND. Other pytest arguments are forwarded.

A tag that does not match a registered test produces pytest's no-tests exit status. A malformed tag fails wrapper validation before pytest starts. The wrapper propagates pytest's exit status.

### 4.2 Direct pytest commands

Direct pytest is useful for explicit paths, custom result directories, or CI-style invocation:

    python -m pytest tests/api/shop -m api \
      --alluredir=reports/api/allure-results \
      --clean-alluredir

    python -m pytest tests/browser/shop -m browser --browser firefox \
      --alluredir=reports/firefox/allure-results \
      --output=reports/firefox/playwright \
      --html=reports/firefox.html --self-contained-html \
      --junitxml=reports/firefox.xml

Direct pytest does not source .env. Export configuration values in the calling shell before invoking it. Pytest defaults from pytest.ini include tests/ discovery, the configured import paths, Allure results at reports/allure-results, Playwright output at reports/playwright, and cleanup of the default Allure directory.

### 4.3 Wrapper behavior and precedence

The wrapper changes into the repository root, sources .env as shell syntax when the file exists, and exports its assignments. This means values in .env can overwrite values exported before the wrapper is launched. Treat .env as executable shell input and keep it under version control ignore rules.

The Python interpreter selection order is:

1. The interpreter named by PYTHON, if set.
2. .venv/bin/python, if it exists and is executable.
3. python from PATH.
4. python3 from PATH.

The wrapper writes results to reports/<lowercase-tag>/allure-results and clears that tag's result directory before the run. Direct pytest instead uses pytest.ini defaults unless an explicit --alluredir is passed. Avoid concurrent runs that share the same output directory.

Pytest arguments may come from pytest.ini, PYTEST_ADDOPTS, and the invocation. The platform plugin reads browser-related environment defaults only when the corresponding long option was not already present in those argument sources. Explicit CLI settings are therefore the clearest way to override a browser default.

## 5. Browser configuration and execution

### 5.1 Browser engines and profiles

Supported browser engines are Chromium, Firefox, and WebKit, assuming the corresponding Playwright browser binary is installed. Select a single engine with --browser chromium, --browser firefox, or --browser webkit. Multiple --browser options may request several engines in one pytest process.

BROWSER_PROFILE selects Playwright device emulation when --device is not explicitly provided:

| BROWSER_PROFILE | Resolved device |
|---|---|
| desktop | No device emulation |
| mobile | Pixel 7 |
| iphone | iPhone 13 |
| ipad | iPad (gen 5) |
| Any other accepted value | Treated as an exact Playwright device name |

If a selected device name is not present in the installed Playwright registry, setup fails with a usage error. Device emulation changes browser context settings; it does not launch a native mobile session.

The browser target URL is LoginPage.BASE_URL in src/domains/browser/shop/login_page.py. The login method accepts explicit credentials or reads WEB_USERNAME and WEB_PASSWORD when omitted. Both values are required.

### 5.2 Browser recordings

The environment can select headed mode, tracing, video, and HAR behavior:

- PLAYWRIGHT_HEADED accepts on or off. The example environment sets on; CI sets off.
- PLAYWRIGHT_TRACING accepts on, off, or retain-on-failure.
- PLAYWRIGHT_VIDEO accepts on, off, or retain-on-failure.
- PLAYWRIGHT_HAR accepts on or off and defaults to off in code.
- PLAYWRIGHT_HAR_DIR defaults to reports/playwright/har.

The project-level context fixture uses pytest-playwright's context factory. When HAR is enabled, it creates the output directory and names a per-test HAR using a sanitized test name and a short hash of the pytest node ID. Playwright trace/video behavior follows pytest-playwright options and the configured output root. Preserve these artifacts only where their diagnostic value justifies their storage and data exposure.

## 6. Configuration reference

### 6.1 Runtime variables

| Variable | Code default | Behavior and validation |
|---|---|---|
| WEB_USERNAME | None | Required for SauceDemo login unless passed explicitly to LoginPage.login() |
| WEB_PASSWORD | None | Required for SauceDemo login unless passed explicitly |
| BROWSER_PROFILE | desktop | desktop, mobile, iphone, ipad, or an exact Playwright device name; explicit --device takes precedence |
| PLAYWRIGHT_BROWSER | Playwright/plugin default when unset | Accepts chromium, firefox, or webkit; an explicit browser option takes precedence |
| PLAYWRIGHT_HEADED | Plugin default when unset | Accepts on or off |
| PLAYWRIGHT_TRACING | Plugin default when unset | Accepts on, off, or retain-on-failure |
| PLAYWRIGHT_VIDEO | Plugin default when unset | Accepts on, off, or retain-on-failure |
| PLAYWRIGHT_HAR | off | Accepts on or off |
| PLAYWRIGHT_HAR_DIR | reports/playwright/har | Destination for HAR recordings |
| APPIUM_SERVER_URL | http://127.0.0.1:4723 | Must be HTTP(S) with a host and valid port; automatic process startup is restricted to unreachable HTTP loopback |
| MOBILE_PLATFORM | Android | Case-insensitive Android or iOS |
| MOBILE_DEVICE_NAME | Android Emulator | Appium deviceName capability |
| MOBILE_UDID | None | Optional device identifier passed as udid when nonempty |
| MOBILE_APP_PATH | None | Required for a mobile run; local file or URL must be accessible to Appium host |
| MOBILE_APP_WAIT_ACTIVITY | None | Optional Android appWaitActivity capability; ignored for iOS |
| PYTEST_ADDOPTS | Empty | Standard pytest arguments included in option-default detection |
| PYTHON | Empty | Optional interpreter override for run_tests.sh |

The .env.example file supplies values that differ from code defaults, including visible Chromium, retain-on-failure trace/video, a Pixel AVD name, and an Android app URL. The example is a starting profile, not a guarantee that the machine has those binaries, devices, accounts, or host tools installed.

### 6.2 Target configuration

The API base URL is a source constant in ProductsPage.BASE_URL. The browser URL is a source constant in LoginPage.BASE_URL. Request paths, selectors, and assertions are specific to the demo applications.

To move to another environment, update the relevant target constant and review its related request paths, authentication, selectors, product data, and expected states. Dynamic target selection through environment variables is not currently implemented. Add explicit typed validation and a safe target policy before introducing such selection into a shared CI environment.

Mobile configuration is read once per session by Settings.from_env(). The options builder requires MOBILE_APP_PATH, validates MOBILE_PLATFORM, and constructs the corresponding UiAutomator2 or XCUITest options. Android capabilities may include udid and appWaitActivity; iOS capabilities may include udid.

## 7. Test development and extension

### 7.1 Scenario design

Place new tests under tests/<platform>/<domain>/. Keep each scenario focused on a user-visible or API-visible outcome. Apply the registered platform and domain markers, and assign a unique test_case ID if the wrapper must select the case.

The reporting plugin maps api, browser, and mobile markers to Allure features. The test_case ID becomes an Allure ID and tag. The markers shop and regression are useful selection/classification labels but do not create special execution behavior. The smoke marker is registered but unused by the current scenarios.

For parametrized tests, put the case marker on each pytest.param entry so every generated test has its own case ID. The pytest display id and the test_case id serve different purposes.

### 7.2 API scenario pattern

The API fixture provides a function-scoped Playwright APIRequestContext with an Accept: application/json header. ProductsPage performs GET /products/{id}; the scenario checks the status and response data.

A new API scenario should preserve this division: request construction and endpoint-specific methods go in the API domain object; response expectations and business assertions stay in the test. Add explicit timeouts or authentication only if the target requires them and document their impact.

### 7.3 Browser scenario pattern

Browser tests consume the pytest-playwright page fixture. Construct the relevant page object with that page, invoke actions, and use Playwright expect assertions for conditions that require waiting on browser state.

LoginPage.login() returns InventoryPage after filling credentials and clicking the login button. InventoryPage owns product-add selectors and cart navigation. CartPage exposes the first cart item locator. Add selectors and actions to the relevant page object; avoid creating a new browser or hidden page-level wait inside a test.

For an initial locator reference, Playwright Codegen can generate a draft against the configured target:

    python -m playwright codegen --target=python-pytest https://www.saucedemo.com

Review generated code, move stable locators/actions into the appropriate object, remove captured credentials/session data, and use the existing page fixture.

### 7.4 Mobile scenario pattern

Mobile tests request mobile_driver and settings. Construct ShopPage with the driver and configured platform. Keep Android resource IDs and iOS accessibility IDs in the mobile domain object. The existing page object uses ten-second explicit waits for element visibility/clickability.

When adding an app flow, validate identifiers on the exact app build used by CI. Prefer explicit state waits over fixed sleeps. Preserve fixture ownership of driver creation and teardown. Make platform-specific behavior explicit when the Android and iOS applications do not expose equivalent controls.

### 7.5 Marker and case-ID maintenance

New markers must be declared in pytest.ini. Keep case IDs unique across the repository as a review rule, because automated uniqueness enforcement is not implemented. If cases move to another management system, define a stable synchronization and ownership policy rather than treating an arbitrary string as globally durable identity.

## 8. Reporting, artifacts, and diagnosis

### 8.1 Result directories and report generation

The pytest wrapper writes raw results under reports/<tag>/allure-results. Direct pytest defaults to reports/allure-results. The Allure configuration reads both the default directory and tag-specific result directories. It writes the static report to reports/allure-report and stores history configuration at reports/allure-history.jsonl.

Commands:

    # Run one case through the Allure wrapper
    npm run test:report -- TEST-04

    # Generate a static report from configured result directories
    npm run report

    # Serve the generated static report on loopback
    npm run report:open

    # Watch for new test output in another terminal
    npm run report:watch

The live watcher writes to reports/allure-live, disables history append, and binds to 127.0.0.1. The report viewer commands also bind to loopback. Allure is a report consumer; it is not required for pytest to execute.

Because the configured report input includes several directories, stale result directories may appear in a generated report. Review or clear the intended input directories before interpreting a report as the outcome of one run. The wrapper clears only the result directory associated with the selected tag.

### 8.2 Allure metadata and failure attachments

The reporting plugin writes Python, OS, pytest, Playwright, and Appium client versions to environment.properties when an Allure result directory is enabled. Case IDs become Allure IDs/tags; platform markers become API, Browser, or Mobile features. Mobile runs also record platform and device parameters.

Test code supplies titles, epics, stories, steps, and scenario-specific attachments. The API suite attaches a response summary containing the request path and HTTP status. On setup or call failures, the plugin attempts a screenshot only if Allure output is enabled and a browser page or mobile driver is available. Browser capture uses a five-second timeout. Mobile screenshot capture temporarily uses a five-second command timeout and restores the previous timeout. If capture fails, the exception type is attached as text and the original failure remains the test failure.

### 8.3 Other test artifacts

Playwright trace and video files use the configured pytest-playwright output location. HAR files are written under PLAYWRIGHT_HAR_DIR when enabled. The local Appium server writes stdout and stderr to reports/appium.log; a subsequent locally managed server start overwrites that file.

CI requests per-job JUnit XML, self-contained pytest-html output, Allure results, and reports/. GitLab retains the artifacts for seven days and uploads them even if the job fails. The pipeline does not combine results from browser/API/mobile jobs into one Allure report and does not persist a cross-pipeline trend history.

Treat reports, screenshots, traces, video, HAR, and Appium logs as potentially sensitive. Their payloads are not redacted by the project.

## 9. Continuous integration

The GitLab pipeline has three stages:

| Stage | Job | Runtime | Behavior |
|---|---|---|---|
| lint | lint | python:3.12-slim | Installs requirements and runs Ruff on src and tests |
| test | api | python:${PYTHON_VERSION}-slim, matrix currently 3.12 | Runs API scenarios and emits Allure, HTML, JUnit, and reports artifacts |
| test | browser | Playwright Python v1.64.0 Noble image, browser matrix chromium/firefox/webkit | Runs browser cases for each selected engine with headed mode off and recordings enabled |
| mobile | android | Runner tagged android; opt-in by RUN_ANDROID=true | Runs mobile cases with an Android app URL; runner must supply Android/Appium infrastructure |
| mobile | ios | Runner tagged macos; opt-in by RUN_IOS=true | Runs mobile cases using a physical-device IPA; runner must supply iOS/Appium infrastructure |

API and browser jobs share the test stage and may run concurrently if runners are available. The mobile stage follows the test stage. The browser matrix varies the engine and does not create a Python-version-by-engine cross-product. The API matrix currently contains one Python version.

Before enabling mobile jobs, ensure the runner can access the Appium server, required SDK/driver, app build, and device. The CI file does not install Appium, mobile drivers, Android SDK, Xcode, or device tooling. Set browser credentials as protected CI/CD variables when the target requires login.

The job artifacts expire after seven days. Change that policy in the pipeline if organizational retention requirements differ, and assess sensitive payload access before broadening retention or visibility.

## 10. Troubleshooting

| Symptom | Checks |
|---|---|
| No cases selected | Check exact, case-sensitive test_case ID; verify -m and -k filters; confirm the test path is included |
| Wrapper rejects the tag | Use all or an identifier beginning with a letter followed by letters, digits, underscores, or hyphens |
| SauceDemo login fails before navigation | Provide WEB_USERNAME and WEB_PASSWORD or pass credentials directly |
| Browser reaches the wrong site | Inspect LoginPage.BASE_URL and target-specific credentials |
| Browser executable is missing | Install the matching Chromium, Firefox, or WebKit binary |
| Browser unexpectedly runs headless | Inspect PLAYWRIGHT_HEADED, CLI options, PYTEST_ADDOPTS, and .env loading order; CI sets headed mode off |
| Browser profile is rejected | Use desktop/mobile/iphone/ipad or an exact Playwright device name available in the installed version |
| HAR configuration fails | Use PLAYWRIGHT_HAR=on or off and ensure the configured directory is writable |
| API assertion data changed | Check ProductsPage.BASE_URL, external target availability, network access, and the demo API's current response |
| Mobile options report a missing app | Set MOBILE_APP_PATH to a local path or URL accessible to the Appium host |
| Appium is unreachable | Check APPIUM_SERVER_URL, /status readiness, host routing, Appium process, driver installation, and reports/appium.log |
| Appium will not start automatically | Automatic startup requires an installed appium executable and an unreachable plain HTTP loopback URL |
| Android app fails to install or launch | Confirm Android SDK/tooling, app compatibility, emulator/device state, appWaitActivity, and host-side access to the build |
| iOS app fails to install | Confirm macOS/Xcode/XCUITest setup, UDID/signing, and that the selected build matches Simulator or physical device |
| Result output is stale or mixed | Inspect --alluredir, clean only intended directories, and avoid concurrent writers to the same path |
| CI job remains pending | Check runner availability, tags, opt-in variables, required secrets, and mobile host prerequisites |

## 11. Security, reliability, and data handling

Do not commit browser credentials, access tokens, signing material, or private application data. Keep local values in ignored .env and CI values in protected variables with the minimum required scope. The wrapper sources .env as shell code, so only use a file you control.

Use trusted Appium endpoints. The fixture limits automatic Appium process startup to HTTP loopback; it does not implement remote-server authentication or TLS policy. Configure remote endpoint access control and encryption at the infrastructure layer.

The automation process does not redact screenshots, traces, video, HAR, HTML reports, request data, or Appium logs. Use disposable test accounts and synthetic data, restrict artifact access, and review retention before exposing them outside the engineering team.

Fixture cleanup closes the Playwright API context, browser context through pytest-playwright, Appium driver, and any local Appium process owned by the fixture. Cleanup does not delete or reset backend records, restore a shared user cart, reset an app's persisted state, or release an externally managed device lock. Those behaviors require explicit test-environment or fixture design.

Public demonstration services are convenient for examples but are not deterministic release targets. Network outages, upstream changes, rate limits, and shared state can produce failures independent of a code change. Use controlled environments for release gating.

## 12. Dependency and maintenance policy

Python dependencies are pinned in requirements.txt. Current pins include pytest 9.1.1, Playwright 1.64.0, pytest-playwright 0.10.0, Appium Python Client 6.0.7, allure-pytest 2.16.2, pytest-html 4.2.0, and Ruff 0.17.0. The Allure CLI is pinned to 3.21.0 in package.json and package-lock.json.

When upgrading Playwright, keep the Python package, installed browser binaries, and GitLab Playwright image aligned. When upgrading Appium, verify the client/server/driver capability contract on the host. When updating pytest or pytest-playwright, validate option parsing, fixture names, and hook behavior. Keep dependency changes and configuration changes in the same review when one constrains the other.

Run the configured lint check before submitting:

    python -m ruff check src tests

The repository includes a Pyright configuration but does not currently install Pyright or run a type-check job. Do not interpret the presence of pyrightconfig.json as evidence that type checking has passed.

## 13. Portability and execution topologies

The pytest process can run on a workstation or Linux CI runner and connect to API/web targets over the network. Browser execution requires browser binaries matching the installed Playwright package. Native automation can use a local Appium server or an already-running remote HTTP(S) server.

A remote Appium topology separates the Python test runner from the host with platform tooling. This is especially useful for macOS/XCUITest or managed Android devices. In that topology, the test runner must route to the endpoint and the Appium host must resolve the app path/build. Do not assume a path local to the test runner also exists on the Appium host.

Browser device emulation is not native automation. For example, WebKit with an iPad device descriptor exercises Playwright browser behavior and emulated viewport/device settings; it does not create an iPad Appium session.

The Bash wrapper and POSIX process-group handling are designed for compatible Unix-like environments. The checked-in CI establishes Linux execution for API and browser jobs, and macOS-tagged infrastructure for iOS. Windows compatibility is not validated by the repository.

## 14. Related references

- [System Architecture](ARCHITECTURE.md) — component boundaries, decisions, trade-offs, and adoption
- [Root README](../README.md) — quick start and example commands
- [pytest.ini](../pytest.ini) — pytest defaults and marker registry
- [run_tests.sh](../run_tests.sh) — wrapper implementation
- [GitLab pipeline](../.gitlab-ci.yml) — jobs, matrices, artifacts, and mobile opt-in
- [Source tree](../src/) and [test tree](../tests/) — implementation and example scenarios
