## Objective

Build a proof of concept (POC) where test cases provided in an Excel file can be interpreted by an AI/LLM layer and executed automatically, with the final execution results generated in a format compatible with Allure Reports.

## Description

This project aims to explore and implement an AI-assisted testing workflow. A tester provides test cases in Excel format. The system should:

- Automatically read the provided test steps
- Understand the actions to be performed using an AI/LLM
- Execute those actions on the application under test
- Generate structured execution results

The output must be compatible with Allure reporting, allowing test execution results to be reviewed in a standard test report format.

## Desired Flow

1. **Excel Test Cases**
2. **AI/LLM Interpretation Layer**
3. **Browser Action Execution**
4. **Result Capture**
5. **Allure Report Output**

## Scope of Work

1. **Understand Input Format**
   - Review expected Excel test case format and define required columns:
     - Test Case ID
     - Scenario
     - Preconditions
     - Test Steps
     - Test Data
     - Expected Result

2. **Explore LLM-Based Execution**
   - Investigate how an AI/LLM can read and interpret Excel test case steps and convert them into executable actions.
   - Emphasize actual step interpretation and execution, not just code generation.

3. **Execution Layer**
   - Use an internal automation execution tool such as Playwright (or equivalent) to perform actions like:
     - Navigating to URLs
     - Clicking buttons
     - Entering values
     - Validating text
     - Capturing errors
   - Testers should not be required to manually write automation scripts.

4. **Result Generation**
   - Capture execution results for each test case, including:
     - Passed/Failed status
     - Error details
     - Step-level logs
     - Screenshots on failure (if applicable)

5. **Allure Report Integration**
   - Generate results in a format consumable by Allure Reports.

## Tasks

- Define the standard Excel test case format
- Read test cases from Excel
- Parse test steps using AI/LLM
- Convert interpreted steps into structured actions
- Execute actions through the browser automation layer
- Capture pass/fail result for each step
- Generate output compatible with Allure Reports
- Document limitations and areas for improvement

## Expected Output

- Working POC for Excel-based AI test execution
- Test cases read from Excel
- LLM interprets and executes test steps
- Execution results generated
- Allure report output available
- Documentation of process, issues encountered, and proposed next steps

## Acceptance Criteria

- Excel test cases can be read successfully
- LLM interprets test steps into executable actions
- Actions are executed on the application under test
- Results are captured on a per-step basis
- Allure-compatible test report is generated
- Complete end-to-end flow is demonstrated
