# AI-Assisted Excel Test Automation
## Implementation-Ready Technical Design (v1)

## 1) Purpose

Define a concrete, build-ready architecture for a Python FastAPI system that:
- Ingests Excel-based manual test cases
- Interprets natural-language steps via local Ollama LLM
- Executes actions through Playwright Python
- Captures step-level evidence and failures
- Produces Allure-compatible results

This document is optimized for delivery of a reliable v1 POC, with clear extension paths for v2.

## 2) Scope and Constraints

### In Scope (v1)
- Excel upload and parsing
- Test case normalization
- LLM step interpretation (strict JSON schema)
- Browser execution for core actions
- Per-step pass/fail logs
- Screenshot and HTML snapshot on failure
- Allure results generation
- Run artifact persistence by `run_id`

### Out of Scope (v1)
- Fully autonomous self-healing with complex DOM+LLM loops
- Rich web UI dashboard
- Multi-tenant auth/permissions
- Large-scale parallel execution optimization

### Hard Constraints
- Language/framework: Python + FastAPI
- LLM: local Ollama only
- Browser automation: Playwright Python
- Reporting: Allure-compatible output
- No test locators provided in Excel

## 3) Target Architecture

1. API Layer (`FastAPI`)
2. Orchestrator Layer (`RunManager` + background job execution)
3. Parser/Normalizer Layer (`ExcelParser`, `TestcaseNormalizer`)
4. Interpretation Layer (`OllamaClient`, `StepInterpreter`)
5. Execution Layer (`TestRunner`, `ActionExecutor`, `LocatorEngine`)
6. Evidence/Reporting Layer (`ArtifactService`, `AllureWriter`)
7. Persistence Layer (`StorageService`)

## 4) Repository Structure

```text
app/
  main.py
  config.py

  api/
    routes/
      test_routes.py

  core/
    logger.py
    exceptions.py
    constants.py

  models/
    request_models.py
    response_models.py
    testcase_models.py
    run_models.py

  services/
    storage_service.py
    excel_parser.py
    testcase_normalizer.py
    ollama_client.py
    step_interpreter.py
    locator_engine.py
    selector_cache.py
    action_executor.py
    test_runner.py
    run_manager.py
    artifact_service.py
    report_service.py

  utils/
    json_utils.py
    text_utils.py
    time_utils.py

storage/
  uploads/
  runs/

tests/
  unit/
  integration/

requirements.txt
.env.example
README.md
```

## 5) Runtime Sequence

1. User uploads Excel (`/api/tests/upload`), receives `file_id`.
2. User starts execution (`/api/tests/run`) with `file_id`, `environment`, options.
3. API creates `run_id`, persists metadata, dispatches background job.
4. Background job:
   - Parse Excel to normalized test cases
   - Interpret each step using Ollama
   - Validate interpretation schema
   - Execute case steps in Playwright
   - Capture per-step and per-case artifacts
   - Write summary and Allure results
5. User polls status (`/api/tests/results/{run_id}`).
6. User downloads report (`/api/tests/report/{run_id}`).

## 6) API Contract

### 6.1 POST `/api/tests/upload`
Upload Excel file.

Response:
```json
{
  "success": true,
  "file_id": "f_20260428_001",
  "filename": "ecommerce_cases.xlsx",
  "stored_path": "storage/uploads/f_20260428_001.xlsx"
}
```

### 6.2 POST `/api/tests/run`
Start background execution.

Request:
```json
{
  "file_id": "f_20260428_001",
  "environment": "beta",
  "headless": true,
  "continue_on_failure": true,
  "step_timeout_ms": 30000,
  "max_cases": null
}
```

Response:
```json
{
  "success": true,
  "run_id": "run_20260428_153500_01",
  "status": "queued"
}
```

### 6.3 GET `/api/tests/results/{run_id}`
Return run progress and summary.

Response:
```json
{
  "success": true,
  "run_id": "run_20260428_153500_01",
  "status": "running",
  "counts": {
    "total_cases": 20,
    "passed_cases": 8,
    "failed_cases": 2,
    "skipped_cases": 0,
    "running_cases": 1,
    "pending_cases": 9
  }
}
```

### 6.4 GET `/api/tests/report/{run_id}`
Return report info.

Response:
```json
{
  "success": true,
  "run_id": "run_20260428_153500_01",
  "allure_results_path": "storage/runs/run_20260428_153500_01/allure-results",
  "allure_report_path": "storage/runs/run_20260428_153500_01/allure-report",
  "zip_path": "storage/runs/run_20260428_153500_01/report.zip"
}
```

## 7) Core Data Models

## 7.1 Normalized Test Case
```json
{
  "module": "Login",
  "test_case_id": "TC_LOGIN_001",
  "test_case_name": "Valid login",
  "preconditions": "User is on home page",
  "steps": [
    "Open the website",
    "Click Sign In",
    "Enter email",
    "Enter password",
    "Click Login",
    "Verify dashboard is visible"
  ],
  "test_data": {
    "email": "user@example.com",
    "password": "Password123"
  },
  "expected_result": "User logs in successfully"
}
```

## 7.2 Interpreted Step Schema
```json
{
  "action": "fill",
  "target": "email field",
  "value": null,
  "value_key": "email",
  "assertion": null,
  "confidence": 0.91,
  "missing_value": false
}
```

### Action Enum (v1)
- `goto`
- `click`
- `fill`
- `assert_visible`
- `assert_text`
- `wait`
- `unknown`

## 7.3 Step Execution Result
```json
{
  "step_index": 3,
  "raw_step": "Enter email",
  "interpreted": {
    "action": "fill",
    "target": "email field",
    "value_key": "email"
  },
  "status": "passed",
  "locator_strategy": "label",
  "duration_ms": 812,
  "url": "https://beta.example.com/login",
  "error_type": null,
  "error_message": null,
  "screenshot_path": null
}
```

## 8) Service Interfaces (Implementation Contracts)

All methods below are required contracts for v1.

## 8.1 `StorageService`
- `save_upload(file_bytes: bytes, filename: str) -> UploadedFileMeta`
- `create_run(environment: str, file_id: str) -> RunMeta`
- `get_run_dir(run_id: str) -> Path`
- `write_json(run_id: str, name: str, payload: dict | list) -> Path`
- `write_text(run_id: str, name: str, payload: str) -> Path`
- `copy_upload_to_run(file_id: str, run_id: str) -> Path`

## 8.2 `ExcelParser`
- `parse_excel(file_path: Path) -> list[RawExcelRow]`
- `detect_columns(columns: list[str]) -> ColumnMap`
- `split_steps(raw_steps: str) -> list[str]`

## 8.3 `TestcaseNormalizer`
- `normalize(raw_rows: list[RawExcelRow]) -> list[NormalizedTestCase]`
- `parse_test_data(raw_test_data: str | None) -> dict[str, str]`
- `validate_required_fields(case: NormalizedTestCase) -> list[str]`

## 8.4 `OllamaClient`
- `generate_json(prompt: str, timeout_s: int = 60) -> dict`
- `healthcheck() -> bool`

## 8.5 `StepInterpreter`
- `interpret_step(step: str, test_data: dict[str, str]) -> InterpretedStep`
- `interpret_case_steps(steps: list[str], test_data: dict[str, str]) -> list[InterpretedStep]`
- `repair_invalid_json(raw_text: str) -> dict | None`

## 8.6 `LocatorEngine`
- `resolve(page, action: str, target: str, context: LocatorContext) -> LocatorResult`
- `resolve_from_cache(...) -> LocatorResult | None`
- `resolve_with_heuristics(...) -> LocatorResult | None`

## 8.7 `SelectorCache`
- `get(key: SelectorCacheKey) -> CachedSelector | None`
- `set(key: SelectorCacheKey, selector: str, strategy: str) -> None`
- `invalidate(key: SelectorCacheKey) -> None`

## 8.8 `ActionExecutor`
- `execute_step(page, interpreted_step: InterpretedStep, case: NormalizedTestCase, ctx: ExecutionContext) -> StepExecutionResult`

## 8.9 `TestRunner`
- `run(run_meta: RunMeta, cases: list[NormalizedTestCase], options: RunOptions) -> RunSummary`
- `run_case(...) -> CaseExecutionResult`

## 8.10 `ReportService`
- `write_allure_results(run_id: str, summary: RunSummary) -> Path`
- `generate_allure_report(run_id: str) -> Path | None`
- `zip_report(run_id: str) -> Path | None`

## 9) Prompting and Interpretation Rules

## 9.1 System Prompt Rules
- Output JSON only.
- Use action enum only.
- Do not invent credentials or hidden data.
- If value required and missing, set `missing_value=true`.
- Use lower-case normalized `target`.

## 9.2 Confidence Policy
- `confidence >= 0.80`: execute normally
- `0.60 <= confidence < 0.80`: execute with warning flag
- `< 0.60`: mark step `needs_clarification` and skip by default

## 9.3 JSON Validation
- Parse JSON
- Validate against Pydantic schema
- Retry once with repair prompt on parse failure
- If still invalid, record `INTERPRETATION_ERROR`

## 10) Locator Strategy

Resolution order:
1. Selector cache
2. Role-based locator
3. Label-based locator
4. Placeholder-based locator
5. Text locator
6. Heuristic by input type
7. Fail with evidence

Important:
- No hardcoded page-specific selectors in generic engine.
- Add per-project optional mapping file only if needed (`selector_overrides.json`).

## 11) Execution Rules

## 11.1 Test Case Lifecycle
- Start case context
- Open fresh page/context
- Navigate to base URL if needed
- Execute steps in order
- Record each step result
- On first step failure:
  - capture screenshot + HTML + URL
  - mark case failed
  - continue to next case if configured

## 11.2 Timeouts and Retries
- Global page timeout: config default (30s)
- Per-step timeout: configurable
- Locator retry: max 1 additional strategy retry
- LLM call retry: max 1 retry on malformed response

## 11.3 Environment Control
- Allowed environments: `beta`, `live`
- Base URLs from env only
- For `live`, optional safe mode that blocks destructive actions

## 12) Error Taxonomy

Use standardized error codes:
- `INPUT_ERROR`
- `NORMALIZATION_ERROR`
- `INTERPRETATION_ERROR`
- `LOCATOR_ERROR`
- `EXECUTION_ERROR`
- `ASSERTION_ERROR`
- `INFRA_ERROR`
- `REPORTING_ERROR`

Every failure record must include:
- `error_type`
- `error_message`
- `step_index`
- `test_case_id`
- `run_id`

## 13) Artifact Model

Per run:
```text
storage/runs/{run_id}/
  input.xlsx
  normalized_testcases.json
  interpreted_steps.json
  execution_summary.json
  logs/run.log
  screenshots/
  html/
  allure-results/
  allure-report/
  report.zip
```

## 14) Observability

Structured logs must include:
- `run_id`
- `test_case_id`
- `step_index`
- `action`
- `target`
- `status`
- `duration_ms`
- `locator_strategy`
- `error_type`

Health checks:
- `GET /health`
  - app status
  - Ollama connectivity
  - writable storage check

## 15) Configuration

Required `.env` entries:
- `APP_NAME`
- `OLLAMA_URL`
- `OLLAMA_MODEL`
- `BETA_BASE_URL`
- `LIVE_BASE_URL`
- `DEFAULT_TIMEOUT`
- `STEP_TIMEOUT_MS`
- `HEADLESS`
- `SCREENSHOT_ON_FAILURE`
- `CACHE_SELECTORS`
- `SAFE_MODE_LIVE`

## 16) Security and Safety

- Never log sensitive credential values.
- Mask known secret keys in artifacts (`password`, `token`, etc.).
- Restrict navigation to allowed base URL domains.
- Disable destructive live actions by default in safe mode.

## 17) Testing Strategy

## 17.1 Unit Tests
- Excel column detection and step splitting
- Test data key-value parsing
- Interpretation schema validation
- Locator strategy ordering
- Error mapping behavior

## 17.2 Integration Tests
- Upload + run API lifecycle
- Mocked Ollama responses
- Playwright execution on sample app
- Artifact generation checks

## 17.3 Acceptance Tests
- Run a real Excel file with at least 5 test cases
- Validate step-level outputs and Allure folder generation

## 18) Implementation Plan and Gates

## Phase 1 - Platform Foundation
Deliver:
- FastAPI app scaffolding
- Upload endpoint
- Storage service
- Run metadata lifecycle

Exit Criteria:
- Excel file can be uploaded and persisted.

## Phase 2 - Parsing and Normalization
Deliver:
- Excel parser with flexible columns
- Step splitter
- Testcase normalization JSON

Exit Criteria:
- `normalized_testcases.json` generated for sample input.

## Phase 3 - LLM Interpretation
Deliver:
- Ollama client
- Step interpreter + schema validation
- `interpreted_steps.json` persisted

Exit Criteria:
- 90%+ steps parse to valid schema on curated sample set.

## Phase 4 - Execution Engine v1
Deliver:
- Playwright runner
- Action executor for v1 actions
- Failure screenshots + HTML capture

Exit Criteria:
- End-to-end execution works for at least 3 sample testcases.

## Phase 5 - Reporting and APIs
Deliver:
- Execution summary generation
- Allure results writing
- Results and report endpoints

Exit Criteria:
- Allure-compatible output created under run directory.

## Phase 6 - Hardening
Deliver:
- Selector cache
- Retry tuning
- Enhanced error reporting
- Live safe mode controls

Exit Criteria:
- Flake rate reduced on repeated sample runs.

## 19) QA Authoring Guidelines (Mandatory for Accuracy)

- One action per step.
- Use explicit target names (button/field text).
- Avoid ambiguous words: "submit", "check", "verify success" without detail.
- Include required values in `Test Data`.
- Write expected outcomes with exact text or URL/state.

Example:
- Weak: `Click submit and verify success`
- Strong: `Click "Place Order" button in checkout summary and verify toast "Order placed successfully"`

## 20) Known Limitations (v1)

- Natural language ambiguity cannot be eliminated fully.
- Locator heuristics may fail on heavily dynamic UIs.
- No advanced recovery flows (captcha, MFA, complex iframes).
- Confidence-based skips may require manual testcase refinement.

## 21) Definition of Done (v1)

v1 is complete when all are true:
- Upload -> Run -> Results -> Report flow works end-to-end.
- Testcases execute without manual locator input in Excel.
- Per-step pass/fail with evidence is available.
- Allure-compatible artifacts generated.
- Artifacts are persisted per run in deterministic structure.
- Known limitations and authoring guidelines are documented.

## 22) Next-Step Backlog (v2+)

- DOM-assisted LLM selector fallback with confidence gating
- Auth/precondition plugins (login/profile setup)
- Parallel execution workers with resource scheduling
- UI dashboard for run monitoring and artifact browsing
- Historical analytics on flaky steps and locator failures

