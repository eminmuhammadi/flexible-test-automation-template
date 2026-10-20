# System Architecture and Engineering Decisions

**System:** QA Automation Platform  
**Document type:** Current-state architecture and decision record  
**Audience:** Principal and staff engineers, QA automation engineers, platform owners, and release engineering  
**Status:** Describes the implementation on the default branch; recommendations and future-state guidance are identified separately

## 1. Executive summary

This repository is a Python test application that composes API, browser, and native mobile checks through pytest. It is executed as a command-line process on an engineer workstation or in a GitLab CI job. The process creates short-lived client contexts and sessions, invokes external application targets, evaluates assertions, and writes machine-readable and human-readable test evidence.

The platform deliberately shares orchestration and reporting conventions while keeping the interaction APIs specific to each surface:

- Playwright's synchronous API request context drives the API examples.
- Playwright pages and locators drive browser journeys.
- Appium's WebDriver client, with UiAutomator2 or XCUITest capabilities, drives native mobile journeys.
- Pytest fixtures control the lifecycle of those resources.
- Allure metadata and attachments provide a common reporting vocabulary.
- GitLab CI runs lint, API, and browser jobs by default, with mobile jobs enabled explicitly on prepared runners.

The central architectural boundary is between **scenario intent**, **application interaction**, and **execution infrastructure**. Scenario code declares the expected behavior. Domain objects hold target-specific request paths, selectors, and actions. The platform package composes pytest options, fixtures, mobile capabilities, lifecycle, and diagnostics.

This is a starter automation harness with concrete examples, not a self-contained product-quality test platform. The checked-in examples target public demonstration services. The repository does not provision those targets, create isolated application data, manage devices, redact artifacts, synchronize cases with a test-management service, or calculate release-quality metrics. Teams adopting it must supply those operating capabilities and validate the signal against their own applications.

## 2. Scope, context, and system boundary

### 2.1 In scope

The system owns:

- Pytest discovery, marker-based selection, fixture composition, and process exit status.
- Creation and cleanup of Playwright API contexts, browser contexts/pages, and Appium driver sessions.
- Resolution of local browser and mobile runtime settings.
- Optional local Appium server startup for an unreachable HTTP loopback endpoint.
- Reusable domain interaction code for the included demo targets.
- Allure case labels, environment metadata, and best-effort failure screenshots.
- Local test entry points and the GitLab pipeline definition.

### 2.2 Outside the repository boundary

The following are external dependencies or responsibilities:

- API and web target availability, test accounts, credentials, data reset, and target-side state.
- Browser binaries, operating system images, network egress, and CI runner capacity.
- Appium server operation, device or simulator provisioning, app signing, Android SDK, Xcode, and platform drivers.
- Secret storage, artifact access policy, report retention beyond configured GitLab artifacts, and operational alerting.
- Test-management synchronization, release policy, ownership routing, flaky-test governance, and suite-level service-level objectives.

The test process has outbound trust relationships with API/web targets and the Appium endpoint. A remote Appium host additionally receives app paths and capabilities and controls a real or virtual device. Its network location is not inferred from the test target URL.

### 2.3 Current example coverage

The current suite defines seven case IDs when one browser engine is selected:

| Surface | Case IDs | Behavior | Implementation |
|---|---|---|---|
| API | TEST-01 through TEST-03 | Read three product records and assert status, ID, nonempty title, and approximate price | Playwright API request context and Fake Store API |
| Browser | TEST-04 through TEST-06 | Sign in to SauceDemo, add one of three products, and verify the first cart item | Playwright page objects and browser fixtures |
| Native mobile | TEST-07 | Add a catalog product and assert the cart displays one item | Appium WebDriver and Sauce Labs My Demo App |

Selecting multiple browser engines repeats the three browser cases per engine. These are demonstration examples. They do not imply production application coverage, cross-device compatibility, performance testing, or a validated release gate.

## 3. Architectural decomposition

### 3.1 Runtime composition

The repository is organized as four cooperating code areas:

| Area | Location | Responsibility |
|---|---|---|
| Scenario suite | tests/ | Express user/API behavior, apply markers and case IDs, make assertions, and attach scenario-specific context |
| Target adapters | src/domains/ | Encapsulate target URLs, endpoint paths, selectors, UI actions, and platform-specific waits |
| Execution platform | src/platform/ | Configure pytest defaults, construct capabilities, create/close resources, and register reporting hooks |
| Tooling and delivery | Repository root | Pin dependencies, define pytest/Ruff settings, provide the shell wrapper and Allure CLI commands, and describe GitLab jobs |

The tests directory loads platform_plugin through tests/conftest.py. The platform plugin declares reporting_plugin as a pytest plugin, so fixtures and hooks are registered as part of test startup. Pytest's configured import roots are src and src/platform; documented commands assume execution from the repository root.

The architecture is an in-process composition, not a separately deployed service. There is no central control plane, queue, persistent database, API server, or remote test scheduler in this repository. GitLab and its runners provide job scheduling; pytest remains the test process and execution authority.

### 3.2 Scenario and domain boundary

Scenario modules under tests/<surface>/<domain>/ own the behavior contract and the final assertions. They also own pytest markers, Allure steps, and test-case IDs. Parametrized examples attach the test_case marker to each pytest parameter so that each generated case can be selected independently.

Domain objects under src/domains/<surface>/<domain>/ accept an already-created Playwright context, page, or Appium driver. They do not create sessions and do not own resource teardown. Their current responsibilities are intentionally concrete:

- ProductsPage holds the Fake Store API base URL and the GET /products/{id} request.
- LoginPage holds the SauceDemo base URL, login selectors, credential resolution, and navigation to InventoryPage.
- InventoryPage and CartPage hold SauceDemo selectors and actions for product and cart flows.
- ShopPage holds My Demo App Android resource IDs, iOS accessibility IDs, explicit waits, and cart interactions.

The package name domains is an organizational convention for target-specific automation code. It does not represent a business-domain model, a shared cross-platform abstraction, or a claim that API, browser, and native interactions have interchangeable semantics. Platform differences remain explicit in code.

This division allows a selector or endpoint change to be made in an adapter while leaving a stable behavioral assertion intact. It does not guarantee that every application change can be isolated to one file: when target behavior or data contracts change, scenario expectations must change with the adapter.

### 3.3 Execution platform

The execution platform is implemented by platform_plugin.py, config/settings.py, mobile/options.py, and reporting_plugin.py.

The platform plugin:

- Reads environment-backed defaults for browser engine, headed mode, tracing, and video unless those options were already supplied through pytest configuration, PYTEST_ADDOPTS, or command-line arguments.
- Resolves browser emulation from the explicit --device option or BROWSER_PROFILE.
- Provides an API request context with an Accept: application/json header and disposes it after the test.
- Wraps Playwright's context factory to optionally record a per-test HAR.
- Loads immutable mobile settings once per pytest session.
- Builds Android or iOS Appium capabilities only when mobile fixtures are requested.
- Reuses a ready Appium server, or starts and owns a local process when narrowly permitted by the endpoint policy.
- Creates a function-scoped driver and calls quit() during fixture teardown.

The reporting plugin adds Allure IDs and tags from test_case markers, maps platform markers to Allure features, adds mobile platform/device parameters, and writes an environment.properties file when Allure output is enabled. It captures a screenshot for setup or call failures when a browser page or mobile driver is available. Screenshot capture is bounded and best-effort; a diagnostic failure is attached as text and must not replace the underlying test failure.

## 4. Resource lifecycle and execution semantics

### 4.1 Scope model

Fixture scope defines client-resource reuse. It is not a mechanism for resetting application state.

| Resource | Scope | Creation and cleanup |
|---|---|---|
| Settings | Session | Read once from environment by Settings.from_env() |
| Browser device selection | Session | Resolve explicit device or profile using Playwright's device registry |
| Mobile capabilities | Session | Validate platform and app path, then construct UiAutomator2Options or XCUITestOptions |
| Appium server | Session, requested only by mobile tests | Reuse ready endpoint; if locally launched, stop only the process owned by this run |
| APIRequestContext | Function | Create per test with JSON Accept header; dispose in finally |
| Browser context/page | Function | Use pytest-playwright fixtures/context factory; optional HAR is attached to context creation |
| Appium WebDriver | Function | Create remote session against configured server; call quit() in finally |

A fresh API request context or browser context limits client-side cookie and storage reuse. A fresh Appium session does not guarantee that the installed application, device, backend account, or remote cart has been reset. Test data isolation and device-state reset need explicit implementation if the selected application retains mutable state across sessions.

### 4.2 Local and remote Appium behavior

The configured APPIUM_SERVER_URL defaults to http://127.0.0.1:4723. Before session creation, the fixture requests the endpoint's /status path with a two-second timeout and requires value.ready to be true.

If the endpoint is unreachable, automatic startup is allowed only when the URL is plain HTTP and its host is localhost or a loopback IP. The plugin locates the appium executable, starts it with the requested host, port, and optional base path, writes output to reports/appium.log, and polls for readiness for up to 30 seconds. The fixture terminates only the process group it started, escalating from SIGTERM to SIGKILL if required.

An HTTP error, malformed response, or unready response is a setup error; the fixture does not interpret these as permission to start a second service. An unreachable remote or HTTPS endpoint is also a setup error and must be started externally. App installation paths and download URLs are resolved from the Appium host's perspective, not necessarily the pytest host's.

### 4.3 End-to-end execution path

A normal run follows this sequence:

1. The engineer or CI job invokes pytest directly or through run_tests.sh.
2. The wrapper changes to the repository root, sources .env as shell code when present, selects an interpreter, translates an optional case tag into a pytest marker, and chooses a tag-specific Allure results directory.
3. Pytest loads tests/conftest.py and the platform plugin. Plugin configuration applies environment defaults only when a corresponding option was not already provided.
4. Pytest collects tests and applies path, marker, case-ID, keyword, and browser-engine filters.
5. A selected test requests its fixtures. Pytest creates only the API, browser, or mobile resources that the test needs.
6. The scenario invokes its target-specific domain object. The object performs requests or UI actions through the fixture-owned resource.
7. The scenario asserts the outcome. Allure receives labels, steps, and any explicit test attachments.
8. On setup or call failure, the reporting hook attempts a screenshot if the corresponding UI resource exists and Allure output is enabled.
9. Pytest tears down function-scoped resources, then returns its exit status. The wrapper propagates that status.
10. A separate Allure CLI command can aggregate raw result files into an HTML report or serve a live view.

### 4.4 Selection and case identity

The wrapper accepts either all or a tag matching the shell pattern for an alphanumeric identifier beginning with a letter. A non-all tag becomes a test_case(id='…') marker expression. When a caller also supplies -m or --markexpr, the wrapper combines the expressions with logical AND. Other arguments are passed through to pytest.

Case IDs are used for wrapper selection and Allure traceability. The current repository does not enforce uniqueness at collection time and does not synchronize the IDs with another system. Unique IDs are a repository review convention. Case IDs do not replace pytest node IDs, pytest keywords, or platform markers.

## 5. Architecture decisions and consequences

### 5.1 Pytest is the execution composition layer

**Decision:** Use pytest discovery, fixtures, hooks, markers, and parametrization as the common execution model.

**Rationale:** These primitives already support the required lifecycle and case selection across API, browser, and mobile tests. A custom runner would duplicate collection, filtering, setup/teardown, error reporting, and exit-code semantics without a demonstrated requirement.

**Consequence:** Contributors need working knowledge of pytest fixture resolution, plugin loading, marker behavior, and hook ordering. Cross-cutting behavior belongs in fixtures or hooks rather than handwritten per-test setup.

### 5.2 Playwright is shared by HTTP and browser scenarios

**Decision:** Use Playwright's Python client for API request contexts and browser interactions.

**Rationale:** The current API layer is a small read-only wrapper, and the same pinned dependency supports browser locator and wait behavior. The split between request context and browser page is explicit, while dependency and version management remain consolidated.

**Consequence:** API tests inherit Playwright request behavior and dependency lifecycle. They do not require browser launch, but the package is still installed. If API requirements grow to need capabilities that are poorly served by this client, introduce another HTTP client only with a documented need and a clear policy for timeouts, authentication, retries, and reporting.

### 5.3 Appium is used for native application coverage

**Decision:** Use Appium WebDriver with UiAutomator2 on Android and XCUITest on iOS.

**Rationale:** These drivers expose native application controls and can run on platform-capable hosts separate from the pytest process.

**Consequence:** Native execution depends on separately provisioned servers, drivers, SDKs, simulators/devices, app builds, and platform-specific identifiers. Sharing pytest selection and reporting does not make mobile infrastructure equivalent to browser infrastructure.

### 5.4 Domain targets are source-controlled constants

**Decision:** Keep the API and browser base URLs in ProductsPage.BASE_URL and LoginPage.BASE_URL. Keep runtime browser and mobile execution options in pytest/environment configuration.

**Rationale:** The target-specific paths and selectors remain adjacent to the interaction methods that use them, while device and recording settings can vary by run.

**Consequence:** Switching API or browser deployment targets currently requires a source change. The architecture does not yet provide a validated environment-target matrix, configuration schema, or protection against accidentally targeting production. If deployment selection becomes dynamic, add a typed and validated target configuration and a safe environment policy rather than scattering raw URL variables through tests.

### 5.5 Allure stores evidence separately from test execution

**Decision:** Pytest writes raw Allure results; the Node.js Allure CLI generates or serves a report independently.

**Rationale:** Test execution can run without an HTML renderer, while developers can inspect results after the process finishes or use a watch command during execution.

**Consequence:** The report must be generated from the intended result directories. Existing result directories can contribute old results, and the wrapper clears the directory associated with its current tag. CI currently uploads per-job artifacts; it does not merge results or preserve an integrated Allure history.

## 6. Quality attributes and trade-offs

### 6.1 Modifiability

The tests/domain/platform separation gives maintainers predictable edit locations. A selector change belongs in a page object; a new scenario belongs in tests; resource ownership belongs in fixtures. This is a useful starting point for small-to-medium suites.

The current adapters remain target-specific, which avoids premature generalized abstractions. As the suite grows, common authentication or data setup may justify separate reusable services, but those should follow repeated behavior rather than anticipate it.

### 6.2 Repeatability and isolation

Function-scoped contexts and sessions reduce state leakage in the automation client. They do not isolate server-side data, users, rate limits, devices, or external demo-service behavior. The API examples assert fixed prices on a public demo API; upstream data changes can produce failures unrelated to a code regression.

For release use, provide controlled test targets, disposable identities, stable test data, explicit reset semantics, and unique resource namespaces where concurrent runs can overlap. Retries are not configured; this preserves the first observed failure but may expose environmental noise.

### 6.3 Observability and diagnosability

The implementation emits Allure IDs/tags, platform features, environment versions, optional HAR, Playwright trace/video, JUnit XML and HTML reports in CI, explicit API response summaries, and best-effort screenshots on UI failure. These artifacts support investigation but can include sensitive content and are not redacted by the reporting plugin.

There is no application-level structured logger, automatic failure classification, integrated CI-to-Allure aggregation job, persistent trend store, or external test-management link. Those are operational extensions, not current capabilities.

### 6.4 Scalability and throughput

The pipeline scales first at the CI job level: API and browser jobs occupy the test stage, and the browser matrix creates separate engine-specific jobs. Actual concurrency depends on runner capacity. Pytest xdist, automatic retries, distributed queues, device locking, and test sharding are not configured.

Mobile parallelism is constrained by physical devices, Appium endpoints, runner availability, and target state. Before increasing concurrency, allocate a distinct device and endpoint per job or serialize jobs; a shared checkout can also create collisions in reports, HAR files, and reports/appium.log.

### 6.5 Portability

Python and browser tests run in Linux CI images. The shell wrapper assumes Bash-compatible behavior. Automatic local Appium process ownership uses POSIX process groups. Android and iOS execution depend on appropriate host platforms and tooling; iOS driver operation requires macOS/Xcode. Windows support is not established by the checked-in pipeline.

### 6.6 Security and privacy

Local credentials belong in ignored .env files; CI credentials belong in protected CI/CD variables. The example environment file contains no browser credentials. Appium endpoints should be trusted and secured by the host/network configuration. The fixture restricts automatic server startup to HTTP loopback but does not configure TLS, authentication, or an Appium server allowlist.

Screenshots, HAR files, video, traces, HTML reports, pytest output, and Appium logs can expose application content, cookies, request metadata, or test data. Apply access controls and retention limits to artifacts; use disposable identities and non-sensitive test data. The GitLab pipeline currently sets a seven-day artifact expiration.

## 7. Delivery topology and CI behavior

The GitLab pipeline defines lint, test, and mobile stages. Ruff runs in a Python 3.12 slim image. API tests run with a Python version matrix containing only 3.12. Browser tests run in the Playwright Python v1.64.0 Noble image, with separate Chromium, Firefox, and WebKit jobs. Android and iOS jobs are skipped unless RUN_ANDROID=true or RUN_IOS=true and require runners tagged android or macos.

The API and browser jobs can run concurrently when runner capacity is available. Mobile jobs run in the later mobile stage after the test stage. The current configuration installs Python dependencies but does not provision mobile SDKs, devices, Appium, or drivers. Those are runner-owner responsibilities.

Each test job requests JUnit XML, a self-contained pytest-html report, Allure results, and applicable Playwright/mobile output. GitLab uploads reports even when the job fails and retains artifacts for seven days. There is no merge step that creates one cross-job Allure report.

The iOS job's configured app is a physical-device IPA. It cannot be used as an iOS Simulator build. A simulator topology requires a simulator-compatible app build and an appropriate macOS runner/device configuration. App signing, device registration, and target availability are outside this repository.

## 8. Operational ownership

| Responsibility | Primary owner | Required operating decision |
|---|---|---|
| Scenario correctness and coverage | Product engineers and QA | Which behaviors are release-critical, how expectations evolve, and who maintains each case |
| Domain adapters | Automation maintainers | How URLs, request paths, selectors, and platform identifiers are updated |
| Fixtures and reporting | Automation/platform maintainers | How lifecycle, diagnostics, output paths, and dependencies remain compatible |
| CI execution | CI platform owners | Runner capacity, network access, protected variables, artifact policy, and required job rules |
| Mobile infrastructure | Mobile platform owners | Devices, Appium endpoints, app build distribution, SDK/Xcode and driver lifecycle |
| Release gating | Release owner | Which cases block promotion, failure ownership, and incident response |

The repository does not currently encode this responsibility model in CODEOWNERS or enforce case ownership. Teams should assign these roles before treating the suite as an operational gate.

## 9. Adoption and evolution guidance

### 9.1 Pilot against a controlled target

Start with a narrow set of business-critical API expectations and customer journeys. Replace the public demo targets with controlled non-production targets, supply disposable accounts and deterministic data, and record baseline execution and diagnosis times. Have a new team member follow the documented setup without undocumented access.

### 9.2 Stabilize the execution contract

Define the required Python and Playwright versions, CI images, browser engines, test environment, credentials, and artifact policy. For mobile, qualify the server/driver/device/app build combination before enabling the job. Confirm that teardown leaves devices and target data in an acceptable state.

### 9.3 Promote evidence-backed gates

Only make a selection required after its target data, ownership, failure response, and runner reliability are understood. Track feedback latency, failure diagnosis time, repeatability on the same revision, maintenance cost, and critical journey coverage. The repository can emit some underlying timings and outcomes, but it does not calculate these organizational measures.

### 9.4 Evolve through explicit decisions

Potential future changes include dynamic target configuration, isolated data provisioning, suite sharding, device locks, artifact redaction, result aggregation, test-management synchronization, and structured failure classification. Each should be introduced in response to an observed operational requirement, with ownership and security impact documented.

Avoid adding a universal abstraction that hides the differences between HTTP, browser, and native UI behavior. Prefer small adapters and explicit lifecycle changes that can be verified against the actual targets.

## 10. Evidence, limitations, and related documentation

This document describes the checked-in implementation in the current source, tests, pytest configuration, dependency pins, Allure configuration, shell wrapper, and GitLab pipeline. It is not a report of successful execution on every browser engine, mobile operating system, or external target. It makes no claim of measured cost reduction, production coverage, or release readiness.

Use the [Technical Guide](README.md) for installation, test selection, configuration, reporting, CI operations, and scenario development. The [root README](../README.md) is the quick-start entry point.
