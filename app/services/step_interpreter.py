"""Convert natural-language steps to structured actions via Ollama."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from app.models.interpreted_models import InterpretedStep
from app.services.ollama_client import OllamaClient
from app.utils.json_utils import extract_json_object

logger = logging.getLogger(__name__)

_SYSTEM_RULES = """You are a test automation step interpreter. Output ONLY valid JSON, no markdown, no explanation.
Rules:
- Keys: action, target, value, value_key, assertion, confidence, missing_value, notes
- action must be one of: goto, hover, click, fill, assert_visible, assert_text, wait, unknown
- target: short lower-case description of UI element or page goal (e.g. "sign in button", "email field")
- If the manual step says hover/mouse over/move cursor over, action must be "hover" (never convert that to goto).
- For fill: use value_key matching test_data keys (e.g. email, password) when the step implies test data; else value literal if given in step
- Do not invent secrets; if credentials needed but not in step text, set missing_value true and value_key if inferable
- For verify/see/check visible UI: assert_visible or assert_text; put expected text in assertion as {"text": "..."} when needed
- confidence: 0.0-1.0
- notes: optional short reason"""

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
            return self._apply_action_overrides(step, self._validate(data))
        except ValidationError:
            repaired = self.repair_invalid_json(text)
            if repaired:
                return self._apply_action_overrides(step, self._validate(repaired))
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
    def _apply_action_overrides(raw_step: str, interpreted: InterpretedStep) -> InterpretedStep:
        """Force deterministic action mapping for high-signal verbs."""
        step = (raw_step or "").strip().lower()
        hover_tokens = ("hover", "mouse over", "move cursor over")
        if any(token in step for token in hover_tokens):
            interpreted.action = "hover"
        return interpreted
