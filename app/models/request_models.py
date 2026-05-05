"""Request payload models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.interpreted_models import InterpretedStep, InterpretedStepRecord


class RunRequest(BaseModel):
    """Start run request payload."""

    file_id: str = Field(..., min_length=1)
    environment: Literal["beta", "live"] = "beta"
    headless: bool = True
    continue_on_failure: bool = True
    step_timeout_ms: int = Field(default=30000, ge=1000)
    max_cases: int | None = Field(default=None, ge=1)
    allow_live_mutations: bool = Field(
        default=False,
        description="Must be true to run click/fill/hover against environment=live.",
    )


class InterpretRunRequest(RunRequest):
    """Interpret-only pipeline: normalize + LLM; no Playwright (same fields as RunRequest)."""


class ExecuteFromInterpretedRequest(BaseModel):
    """Browser execution using existing interpreted_steps.json for a run folder."""

    interpret_run_id: str = Field(..., min_length=1, description="run_id from POST /interpret")
    environment: Literal["beta", "live"] = "beta"
    headless: bool = True
    continue_on_failure: bool = True
    step_timeout_ms: int = Field(default=30000, ge=1000)
    allow_live_mutations: bool = Field(
        default=False,
        description="Must be true to run click/fill/hover against environment=live.",
    )


class StepPatchItem(BaseModel):
    """Partial update for one step row (use model_fields_set semantics via API JSON)."""

    model_config = ConfigDict(extra="forbid")

    step_index: int = Field(..., ge=0)
    raw_step: str | None = None
    interpreted: InterpretedStep | None = None
    interpretation_error: dict[str, str] | None = None


class InterpretedCasePatch(BaseModel):
    """Patch one testcase: either replace all steps or patch individual step rows."""

    model_config = ConfigDict(extra="forbid")

    test_case_id: str = Field(..., min_length=1)
    step_patches: list[StepPatchItem] | None = None
    steps: list[InterpretedStepRecord] | None = Field(
        default=None,
        description="If set, replaces the entire steps array for this testcase.",
    )

    @model_validator(mode="after")
    def _one_update_mode(self) -> InterpretedCasePatch:
        if self.steps is not None:
            if not self.steps:
                raise ValueError("steps must be non-empty when provided")
            if self.step_patches:
                raise ValueError("Use either steps (full replace) or step_patches, not both")
            return self
        if not self.step_patches:
            raise ValueError("Provide step_patches or steps")
        return self


class InterpretedStepsPatchRequest(BaseModel):
    """PATCH body to merge edits into interpreted_steps.json."""

    model_config = ConfigDict(extra="forbid")

    patches: list[InterpretedCasePatch] = Field(..., min_length=1)
    expected_revision: int | None = Field(
        default=None,
        ge=1,
        description="Optimistic lock. If provided and mismatched, API returns conflict.",
    )


class RunListSortOptions(BaseModel):
    """Sort controls for run listing."""

    model_config = ConfigDict(extra="forbid")

    sortBy: Literal["run_id", "file_id", "status", "environment", "created_at", "updated_at"] = (
        "created_at"
    )
    sortOrder: Literal["asc", "desc"] = "desc"


class RunListFilter(BaseModel):
    """Single filter condition for run listing."""

    model_config = ConfigDict(extra="forbid")

    field: Literal["run_id", "file_id", "status", "environment", "created_at", "updated_at"]
    operator: Literal["equals", "contains", "gte", "lte"]
    value: Any


class RunListRequest(BaseModel):
    """POST body for paginated/searchable run listing."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=25, ge=1, le=200)
    search: str | None = None
    sortingOptions: RunListSortOptions = Field(default_factory=RunListSortOptions)
    filters: list[RunListFilter] = Field(default_factory=list)


class CancelRunRequest(BaseModel):
    """Request body for cancelling a running run."""

    reason: str | None = None


class CleanupRunsRequest(BaseModel):
    """Request body for retention cleanup of old run folders."""

    retain_days: int = Field(default=14, ge=1, le=3650)
    dry_run: bool = True
    max_delete: int = Field(default=200, ge=1, le=5000)

