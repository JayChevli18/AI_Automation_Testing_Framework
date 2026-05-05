"""Response payload models."""

from __future__ import annotations

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Upload API response."""

    success: bool
    file_id: str
    filename: str
    stored_path: str


class RunResponse(BaseModel):
    """Run start response."""

    success: bool
    run_id: str
    status: str


class RunCounts(BaseModel):
    """Basic run counts for status API."""

    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    running_cases: int = 0
    pending_cases: int = 0


class RunResultResponse(BaseModel):
    """Run result/status response."""

    success: bool
    run_id: str
    status: str
    counts: RunCounts


class RunExecutionSummaryResponse(BaseModel):
    """Full execution summary response."""

    success: bool
    run_id: str
    summary: dict


class RunReportResponse(BaseModel):
    """Report artifact discovery response."""

    success: bool
    run_id: str
    allure_results_dir: str
    allure_result_files: list[str]
    html_report_path: str


class VersionedExecutionResponse(BaseModel):
    """Response after a versioned browser execution under executions/<id>/."""

    success: bool
    run_id: str
    execution_id: str
    status: str


class VersionedExecutionsListResponse(BaseModel):
    """List of recorded versioned executions for a run."""

    success: bool
    run_id: str
    executions: list[dict]


class VersionedExecutionSummaryResponse(BaseModel):
    """Full execution summary for one versioned execution."""

    success: bool
    run_id: str
    execution_id: str
    summary: dict


class InterpretedStepsPatchResponse(BaseModel):
    """Response after PATCH merged into interpreted_steps.json."""

    success: bool
    run_id: str
    patched_test_case_ids: list[str]
    revision: int | None = None
    message: str = ""


class RunListItem(BaseModel):
    """Single run row for list APIs."""

    run_id: str
    file_id: str
    status: str
    environment: str
    created_at: str
    updated_at: str


class RunListResponse(BaseModel):
    """Legacy response for simple run listing."""

    success: bool
    runs: list[RunListItem]


class RunListMeta(BaseModel):
    """Pagination metadata for run listing."""

    currentPage: int
    totalPages: int
    totalItems: int
    itemsPerPage: int
    hasNextPage: bool
    hasPreviousPage: bool


class RunListData(BaseModel):
    """Data block for paginated run listing."""

    list: list[RunListItem]
    meta: RunListMeta


class RunListPostResponse(BaseModel):
    """POST response for run listing with pagination/filter/search."""

    success: bool
    message: str
    data: RunListData


class InterpretedStepsReadResponse(BaseModel):
    """Read interpreted steps JSON for a run."""

    success: bool
    run_id: str
    interpreted_steps: list[dict]
    revision: int | None = None


class LatestExecutionResponse(BaseModel):
    """Latest versioned execution metadata."""

    success: bool
    run_id: str
    execution_id: str | None
    execution: dict | None = None


class ArtifactIndexResponse(BaseModel):
    """Artifact index response for UI evidence panels."""

    success: bool
    run_id: str
    execution_id: str | None
    artifacts: dict


class CancelRunResponse(BaseModel):
    """Response body for cancellation requests."""

    success: bool
    run_id: str
    status: str
    message: str


class CleanupRunsResponse(BaseModel):
    """Response for retention cleanup."""

    success: bool
    message: str
    deleted_run_ids: list[str]
    scanned: int

