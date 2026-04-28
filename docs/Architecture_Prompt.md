I want to build a Python FastAPI project for AI-assisted automation testing of an ecommerce website.

Project Goal:
Build a proof-of-concept system where a user uploads an Excel sheet containing manual, module-wise test cases. The backend reads the Excel, interprets natural-language test steps using a local Ollama LLM, executes those steps in a browser using Playwright Python, captures pass/fail results and screenshots on failure, and generates Allure-compatible test reports.

Important Constraints:
- Use Python + FastAPI.
- Use only local LLM through Ollama.
- Do not use OpenAI, Claude, or any cloud LLM.
- Use Playwright Python for browser automation.
- Use Allure for reporting.
- Test cases will not contain locators, XPath, CSS selectors, or data-testid.
- Test cases are written in natural language/manual QA format.
- System should support beta and live environments.
- The project should be structured cleanly and production-style.

Main Flow:
Excel Upload
→ Excel Parser
→ Test Case Normalizer
→ Ollama Step Interpreter
→ Playwright Execution Engine
→ Smart Locator Engine
→ Screenshot/Error Capture
→ Allure Result Generation
→ Report Download/API Response

Architecture:

1. FastAPI Layer
Responsibilities:
- Upload Excel file.
- Start test execution.
- Return execution status.
- Provide result summary.
- Provide generated report path or downloadable report.

Required APIs:
POST /api/tests/upload
- Accept Excel file.
- Save file in uploads directory.
- Return file_id.

POST /api/tests/run
- Input:
  {
    "file_id": "uploaded-file-id",
    "environment": "beta" or "live",
    "headless": true or false
  }
- Parse test cases.
- Execute all test cases.
- Generate Allure results.
- Return execution summary.

GET /api/tests/results/{run_id}
- Return pass/fail summary.

GET /api/tests/report/{run_id}
- Return path/download link for generated Allure report.

2. Excel Parser Layer
Use pandas/openpyxl.
The Excel may contain module-wise test cases.
Parser should be flexible and handle column names like:
- Module
- Test Case ID
- Test Case Name
- Scenario
- Preconditions
- Test Steps
- Test Data
- Expected Result

If steps are multiline, split them by:
- newline
- numbered steps like 1., 2., 3.
- bullets
- semicolon if needed

Output normalized structure:
[
  {
    "module": "Login",
    "test_case_id": "TC_LOGIN_001",
    "test_case_name": "Valid login",
    "preconditions": "...",
    "steps": [
      "Open the website",
      "Click on sign in icon",
      "Enter valid email",
      "Enter valid password",
      "Click on login button",
      "Verify user lands on dashboard"
    ],
    "test_data": {
      "email": "user@example.com",
      "password": "Password123"
    },
    "expected_result": "User should login successfully"
  }
]

3. Test Case Normalizer
Responsibilities:
- Clean empty rows.
- Remove duplicate spaces.
- Normalize module names.
- Convert each test case into standard JSON.
- If test data exists as plain text, convert it into key-value pairs where possible.

Example:
"Email: test@test.com, Password: 123456"
should become:
{
  "email": "test@test.com",
  "password": "123456"
}

4. Ollama LLM Layer
Use local Ollama REST API:
http://localhost:11434/api/generate

Create an Ollama client service.
Model should be configurable using .env:
OLLAMA_MODEL=llama3.1
OLLAMA_URL=http://localhost:11434

Responsibilities:
- Convert each natural-language step into structured action JSON.
- Return only valid JSON.
- No explanation text.

Supported actions:
- goto
- click
- fill
- select
- check
- uncheck
- hover
- wait
- assert_visible
- assert_text
- assert_url
- assert_title
- press
- scroll
- unknown

Example input step:
"Click on Sign In Icon in the Navbar"

Expected LLM output:
{
  "action": "click",
  "target": "sign in icon",
  "value": null,
  "assertion": null
}

Example input:
"Enter valid email"

Expected output:
{
  "action": "fill",
  "target": "email field",
  "value_key": "email",
  "value": null,
  "assertion": null
}

If value is available from test_data, execution engine should resolve value_key from test_data.

Prompt rules:
- Always return JSON only.
- Use lower-case target names.
- Do not invent credentials.
- If a value is required but missing, return value_key or mark missing_value as true.
- For verification steps, use assert_visible, assert_text, assert_url, or assert_title.

5. Smart Locator Engine
Since Excel has no locators, create a smart locator resolver.

Resolution order:
1. Cached selector
2. Playwright role-based locator
3. Label-based locator
4. Placeholder-based locator
5. Text-based locator
6. Input type heuristic
7. Button/link heuristic
8. Ollama DOM-based selector fallback
9. Fail with screenshot

Locator strategies:

For click:
- page.get_by_role("button", name=target)
- page.get_by_role("link", name=target)
- page.get_by_text(target)
- page.locator("button").filter(has_text=target)
- page.locator("a").filter(has_text=target)

For fill:
- page.get_by_label(target)
- page.get_by_placeholder(target)
- if target contains "email": input[type=email], input[name*=email], input[id*=email]
- if target contains "password": input[type=password]
- if target contains "search": input[type=search], input[name*=search], input[placeholder*=search]

For assert:
- page.get_by_text(target)
- page.locator("*").filter(has_text=target)

6. Selector Cache / Self-Healing
Create selector_cache.json.
When a locator succeeds, save it:
{
  "environment": {
    "target": {
      "selector": "...",
      "strategy": "role/text/css",
      "last_success": "timestamp"
    }
  }
}

On next run:
- Try cached selector first.
- If it fails, remove/update cache.
- Try smart locator again.
- If successful, update cache.

7. Ollama DOM Selector Fallback
If smart locator fails:
- Get simplified DOM from current page.
- Do not send full huge HTML.
- Extract visible elements:
  - tag
  - text
  - role
  - aria-label
  - placeholder
  - name
  - id
  - class
  - type
  - href

Send to Ollama:
Task:
Find the best CSS selector for the target action.

Input:
- action
- target
- simplified DOM list

Output:
{
  "selector": "input[type='email']",
  "confidence": 0.82,
  "reason": "matches email input"
}

Only use selector if confidence >= 0.6.

8. Playwright Execution Engine
Use async Playwright.

Execution flow:
For each test case:
- Start Allure test context.
- Open browser/page.
- Navigate to base URL if first step is not goto.
- Execute each interpreted step.
- Attach step logs.
- On failure:
  - capture screenshot
  - capture current URL
  - capture HTML snapshot
  - attach to Allure
  - mark test failed
- Continue next test case depending on config.

Browser config:
- headless from API input
- timeout configurable
- slow_mo optional
- viewport configurable

Supported environments:
.env:
BETA_BASE_URL=https://beta.example.com
LIVE_BASE_URL=https://example.com

9. Action Executor
Implement action handling:

goto:
- If target is full URL, go directly.
- If target is path, combine with base_url.
- If target is "home page" or "website", go to base_url.

click:
- Resolve element using locator engine.
- Click.

fill:
- Resolve value:
  - direct value from LLM
  - value_key from test_data
  - fallback from config test credentials
- Resolve element.
- Fill.

select:
- Resolve dropdown.
- Select option.

assert_visible:
- Resolve target.
- Expect visible.

assert_text:
- Verify text exists on page.

assert_url:
- Verify current URL contains expected value.

wait:
- Wait for timeout or page load.

unknown:
- Log as skipped or failed based on config.

10. Allure Reporting
Use allure-pytest or manually generate Allure result JSON.
Recommended for first version:
- Generate Allure-compatible result files manually or run execution through pytest wrapper.

Simpler POC:
- During execution, write JSON result summary.
- Also generate Allure result JSON files into:
reports/{run_id}/allure-results

Attach:
- screenshots
- error messages
- step logs
- current URL
- page snapshot path

Then allow user to generate report with:
allure generate reports/{run_id}/allure-results -o reports/{run_id}/allure-report --clean

Also create an API to zip report.

11. Database / Storage
For POC, use file-based storage.

Folders:
storage/
  uploads/
  runs/
  screenshots/
  html_snapshots/
  reports/

Each run should have run_id:
runs/{run_id}/
  input.xlsx
  normalized_testcases.json
  interpreted_steps.json
  execution_summary.json
  screenshots/
  html/
  allure-results/
  allure-report/

12. Project Folder Structure

Create this structure:

app/
  main.py
  config.py

  api/
    routes/
      test_routes.py

  core/
    logger.py
    exceptions.py

  models/
    request_models.py
    response_models.py
    testcase_models.py

  services/
    excel_parser.py
    testcase_normalizer.py
    ollama_client.py
    step_interpreter.py
    locator_engine.py
    dom_extractor.py
    selector_cache.py
    action_executor.py
    test_runner.py
    report_service.py
    storage_service.py

  utils/
    file_utils.py
    json_utils.py
    string_utils.py

storage/
  uploads/
  runs/

reports/

requirements.txt
.env.example
README.md

13. Required Dependencies

Use these:
fastapi
uvicorn
python-multipart
pandas
openpyxl
playwright
requests
pydantic
python-dotenv
allure-pytest
pytest

Install Playwright browser:
playwright install chromium

14. Config

.env.example:
APP_NAME=AI Test Automation
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
BETA_BASE_URL=https://beta.example.com
LIVE_BASE_URL=https://example.com
DEFAULT_TIMEOUT=30000
HEADLESS=true
SCREENSHOT_ON_FAILURE=true
CACHE_SELECTORS=true

15. Error Handling

Handle:
- Invalid Excel file
- Missing required columns
- Ollama not running
- Invalid JSON from Ollama
- Browser launch failure
- Element not found
- Missing test data
- Assertion failure
- Allure generation failure

Return clean API errors:
{
  "success": false,
  "message": "Ollama is not running",
  "details": "Could not connect to localhost:11434"
}

16. Logging

Use Python logging.
Log:
- uploaded file path
- parsed test count
- each interpreted step
- each executed action
- locator strategy used
- failures
- screenshot paths
- report paths

17. README Requirements

Create README.md with:
- project overview
- architecture diagram in text
- setup instructions
- Ollama setup
- Playwright setup
- running FastAPI
- uploading Excel
- running tests
- generating Allure report
- limitations
- future improvements

18. Development Phases

Build in this order:

Phase 1:
- FastAPI upload API
- Excel parser
- Normalized JSON output

Phase 2:
- Ollama client
- Step interpreter
- Save interpreted steps

Phase 3:
- Playwright execution engine
- Basic actions: goto, click, fill, assert_visible

Phase 4:
- Smart locator engine
- Heuristic locators
- Screenshots on failure

Phase 5:
- Selector cache
- Self-healing retry

Phase 6:
- Allure report integration

Phase 7:
- Clean README and examples

19. Acceptance Criteria

The system is complete when:
- User can upload Excel file.
- System parses module-wise test cases.
- System converts natural-language steps into structured JSON using Ollama.
- System executes test cases on beta or live URL.
- System does not require locators in Excel.
- System captures screenshot on failure.
- System produces execution summary.
- System generates Allure-compatible result folder.
- System stores all run artifacts under a unique run_id.
- Code is modular, clean, and easy to extend.

20. Important Implementation Notes

Do not hardcode selectors.
Do not depend on cloud AI.
Do not stop entire run if one test case fails.
Do not send massive full HTML to Ollama.
Use simplified DOM extraction.
Make prompts strict and JSON-only.
Add fallback if Ollama returns invalid JSON.
Use async Playwright.
Keep FastAPI APIs clean.
Use service-based architecture.
Write code with proper typing where possible.

Now generate the complete project code step by step following this architecture.