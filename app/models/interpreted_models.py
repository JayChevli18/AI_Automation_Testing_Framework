"""Models for LLM-interpreted step actions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

InterpretedAction = Literal[
    "goto",
    "hover",
    "click",
    "fill",
    "assert_visible",
    "assert_text",
    "scroll",
    "wait",
    "unknown",
]


class InterpretedStep(BaseModel):
    """Structured action produced by the step interpreter."""

    action: InterpretedAction
    target: str = ""
    value: str | None = None
    value_key: str | None = None
    assertion: dict[str, Any] | None = None
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    missing_value: bool = False
    notes: str | None = None


class InterpretedStepRecord(BaseModel):
    """One row in interpreted_steps.json for a single manual step."""

    step_index: int
    raw_step: str
    interpreted: InterpretedStep | None = None
    interpretation_error: dict[str, str] | None = None


class InterpretedCaseRecord(BaseModel):
    """Interpreted steps grouped by testcase."""

    test_case_id: str
    test_case_name: str = ""
    module: str = ""
    steps: list[InterpretedStepRecord] = Field(default_factory=list)
