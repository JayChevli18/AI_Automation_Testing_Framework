"""Models for execution results."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StepExecutionResult(BaseModel):
    """Execution result for a single interpreted step."""

    step_index: int
    raw_step: str
    action: str = ""
    target: str = ""
    status: str
    locator_strategy: str | None = None
    duration_ms: int = 0
    url: str | None = None
    attempts: int = 1
    error_type: str | None = None
    error_message: str | None = None
    screenshot_path: str | None = None
    html_snapshot_path: str | None = None


class CaseExecutionResult(BaseModel):
    """Execution result for one testcase."""

    test_case_id: str
    test_case_name: str = ""
    module: str = ""
    status: str
    steps: list[StepExecutionResult] = Field(default_factory=list)


class RunExecutionSummary(BaseModel):
    """Aggregated run summary stored as execution_summary.json."""

    run_id: str
    status: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    running_cases: int = 0
    pending_cases: int = 0
    cases: list[CaseExecutionResult] = Field(default_factory=list)
