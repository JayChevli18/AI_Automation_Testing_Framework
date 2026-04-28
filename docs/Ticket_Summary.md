# Ticket Summary: AI-Driven Excel Test Execution POC (with Local LLM via Ollama)

## Objective

Build a proof of concept (POC) where test cases written in Excel are interpreted by an AI layer (local LLM using Ollama), executed automatically with browser automation (e.g., Playwright), and results are generated in an Allure-compatible format.

---

## End-to-End Flow

1. **Excel test cases input**
2. **LLM interprets each step into executable actions**
3. **Automation engine performs browser actions**
4. **Step-level execution results captured**
5. **Allure report generated**

---

## Feasibility

- **POC feasibility:** High
- **Production reliability (as-is):** Medium
- Using Ollama (local LLM) is feasible and beneficial for privacy/control.
- The main challenge is not Excel reading or Allure reporting, but consistent and accurate natural-language step interpretation.

---

## Key Pros

- Low entry barrier for testers (Excel-first workflow; less scripting needed)
- Faster test creation for repetitive business flows
- Better privacy and data control with local LLM (no external API dependency)
- Reduced external AI cost per call (depends on local infrastructure)
- Standard reporting output through Allure for team visibility

---

## Key Cons / Risks

- Natural language ambiguity can lead to incorrect actions
- Non-deterministic interpretation can reduce repeatability
- Flaky execution due to UI dynamics, timing, and locator instability
- Debugging can be more difficult when failure originates from interpretation, not automation
- Local model quality may be lower than top hosted models for complex instructions
- Local infrastructure/resource limits (CPU/RAM/GPU) can impact speed and concurrency

---

## Likely Issues We May Face

- Same step interpreted differently across runs/models
- Wrong element selection when multiple similar buttons/fields exist
- Assertion confusion (e.g., “success shown”) without exact expected text/location
- Dynamic pages, popups, frames, and loaders causing intermittent failures
- Session/authentication/precondition handling gaps
- Environment/test data instability causing false failures
- Prompt/model version drift over time

---

## Critical Team Guidance (Very Important)

**Accuracy depends heavily on how test steps are written in Excel.**

### Must-follow Excel authoring rules

- Write explicit actions (avoid vague language like “submit” or “check success”)
- Mention the exact UI target (page/section/button text/field label)
- Keep one action per step
- Provide concrete expected results (exact text/state/value)
- Include required test data in structured columns
- Avoid combining multiple validations into one sentence
- Maintain consistent wording patterns across all test cases

**Practical note for team:**  
*Only when Excel steps are precise and standardized will we gain meaningful accuracy. Poorly written or ambiguous test cases will directly reduce AI execution reliability.*

---

## Recommendation for POC Success

- Use a constrained action schema (e.g., `navigate`, `click`, `type`, `assertText`, etc.)
- Validate LLM output before execution (schema + safety checks)
- Add robust waits, retries, timeouts, and failure screenshots
- Maintain full traceability:
  - original Excel step
  - interpreted action
  - executed command
  - result/evidence
- Define fallback for low-confidence interpretation (mark as "needs clarification")

---

## Final Conclusion

This project is worth pursuing and is feasible as a POC with Ollama.  
**Expected outcome:** workable automation acceleration with clear reporting.

However, reliability depends on three pillars:

1. **Strict Excel test case writing standards**
2. **Controlled LLM-to-action conversion**
3. **Strong automation guardrails (locators, waits, retries, logs)**

*If we align on these, we can achieve good accuracy and a strong foundation for future production hardening.*