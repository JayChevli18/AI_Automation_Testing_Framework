"""Convert natural-language steps to structured actions via Ollama."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from app.models.interpreted_models import InterpretedStep
from app.services.ollama_client import OllamaClient
from app.utils.json_utils import extract_json_object

logger = logging.getLogger(__name__)

_SYSTEM_RULES = """You are a test automation step interpreter. Output ONLY one JSON object. No markdown, no prose, no code fences.

Required keys: action, target, value, value_key, assertion, confidence, missing_value, notes
- action must be exactly one of: goto, hover, click, fill, assert_visible, assert_text, wait, unknown

=== goto (navigation only — strict) ===
Use "goto" ONLY when the step is clearly about loading a page by URL or path, for example:
- "Open the website", "Go to https://...", "Navigate to /sign-in", "Open home page"
Do NOT use "goto" if the step says click, tap, press, select, choose, hit, or open a link/button/menu item.
Never use "goto" with target that is only a layout region name (e.g. "header", "footer", "sidebar", "navbar") — those are not URLs.

=== click ===
If the step says click/tap/press (a control) or implies activating a link or button, action MUST be "click".
Examples that MUST be "click", never "goto":
- "In the header, click the Sign In link" -> action click, target "sign in link" (or similar short phrase for the link)
- "Click the Login button" -> action click, target "login button"

=== hover ===
If the manual step says hover / mouse over / move cursor over, action must be "hover" (never "goto").

=== fill ===
When the step is entering data that comes from the test_data keys listed in the user message:
- Set value_key to exactly one of those keys (e.g. email, password).
- Set value to null (JSON null). Never set value to the words "email", "password", or any key name — those are not the real credential values.
- Do not put secrets in value; the runner loads the actual string from test_data using value_key.
If the step gives a literal to type (e.g. a code shown in the step text) and it is NOT in test_data, use value for that literal and value_key null.
Do not invent secrets; if needed but not in step text, set missing_value true and value_key if inferable.

=== assert_text vs assert_visible ===
- If the step quotes specific text to check (e.g. "Assert text X is visible", "Verify message Y", "Popup shows Z"), use action "assert_text" and set assertion to {"text": "..."} with the EXACT expected substring from the step (strip only surrounding quotes). target can repeat that text or be a short label like "expected message".
- Use "assert_visible" only when checking visibility of a named UI element without a fixed literal string (e.g. "dashboard panel is visible").

=== wait ===
Use "wait" only for explicit waits/sleeps; value can be milliseconds as a string if given.

=== target ===
Keep target as a short, lower-case phrase describing the element or navigation intent. Do not put full sentences in target.

=== confidence ===
confidence is a number from 0.0 to 1.0.

=== notes ===
notes is optional, very short reason if needed."""

_USER_TEMPLATE = """test_data keys available: {keys}
manual step: {step}

Return JSON object only."""


class StepInterpreter:
    """LLM-backed interpreter with schema validation and one repair retry."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    def interpret_step(self, step: str, test_data: dict[str, str]) -> InterpretedStep:
        """Interpret one step; raises on unrecoverable LLM/parse failure."""
        keys = ", ".join(sorted(test_data.keys())) if test_data else "(none)"
        prompt = _USER_TEMPLATE.format(keys=keys, step=step.strip())
        text = self.client.generate_text(
            prompt=prompt,
            system_prefix=_SYSTEM_RULES,
            json_format=True,
        )
        data = extract_json_object(text)
        if data is None:
            data = self.repair_invalid_json(text)
        if data is None:
            raise ValueError(f"Could not parse interpreter JSON from: {text[:500]!r}")
        try:
            validated = self._validate(data)
            return self._apply_action_overrides(step, validated, test_data)
        except ValidationError:
            repaired = self.repair_invalid_json(text)
            if repaired:
                return self._apply_action_overrides(step, self._validate(repaired), test_data)
            raise

    def interpret_case_steps(
        self,
        steps: list[str],
        test_data: dict[str, str],
    ) -> list[InterpretedStep]:
        """Interpret all steps in order."""
        return [self.interpret_step(s, test_data) for s in steps]

    def repair_invalid_json(self, raw_text: str) -> dict[str, Any] | None:
        """Ask model to fix output into valid interpreter JSON."""
        repair_prompt = f"""Fix the following into a single JSON object with keys:
action, target, value, value_key, assertion, confidence, missing_value, notes.
Use action enum: goto, hover, click, fill, assert_visible, assert_text, wait, unknown.
Input to fix: {raw_text[:4000]}"""
        try:
            fix_text = self.client.generate_text(
                prompt=repair_prompt,
                system_prefix=_SYSTEM_RULES,
                json_format=True,
            )
            fixed = extract_json_object(fix_text)
            if fixed:
                return fixed
        except ConnectionError:
            pass
        extracted = extract_json_object(raw_text)
        return extracted if isinstance(extracted, dict) else None

    def try_interpret_step(
        self,
        step: str,
        test_data: dict[str, str],
    ) -> tuple[InterpretedStep | None, str | None]:
        """Interpret without raising; returns (interpreted_step, error_message)."""
        try:
            return self.interpret_step(step, test_data), None
        except Exception as exc:
            return None, str(exc)

    @staticmethod
    def _validate(data: dict[str, Any]) -> InterpretedStep:
        return InterpretedStep.model_validate(data)

    @staticmethod
    def _apply_action_overrides(
        raw_step: str,
        interpreted: InterpretedStep,
        test_data: dict[str, str],
    ) -> InterpretedStep:
        """Force deterministic action mapping for high-signal verbs and fill fixes."""
        step = (raw_step or "").strip().lower()
        hover_tokens = ("hover", "mouse over", "move cursor over")
        if any(token in step for token in hover_tokens):
            interpreted.action = "hover"

        if interpreted.action == "fill":
            StepInterpreter._normalize_fill_step(raw_step, interpreted, test_data)

        return interpreted

    @staticmethod
    def _normalize_fill_step(
        raw_step: str,
        interpreted: InterpretedStep,
        test_data: dict[str, str],
    ) -> None:
        """Align value_key with the field mentioned in the step; strip bogus value placeholders."""
        step_l = (raw_step or "").lower()

        # Prefer explicit field phrases, then fall back to keywords (email before password conflicts).
        if (
            "email field" in step_l
            or "wrong email" in step_l
            or "e-mail field" in step_l
        ) and "email" in test_data:
            interpreted.value_key = "email"
        elif ("password field" in step_l or "pwd field" in step_l) and "password" in test_data:
            interpreted.value_key = "password"
        elif "email" in step_l and "password" not in step_l and "email" in test_data:
            interpreted.value_key = "email"
        elif "password" in step_l and "email" not in step_l and "password" in test_data:
            interpreted.value_key = "password"

        vk = interpreted.value_key
        if vk and vk in test_data:
            interpreted.value = None

        bad_placeholders = {
            "",
            "password",
            "email",
            "pwd",
            "e-mail",
            "username",
            "user name",
        }
        if vk:
            bad_placeholders.add(vk.lower())
        v = interpreted.value
        if v is not None and str(v).strip().lower() in bad_placeholders:
            interpreted.value = None
