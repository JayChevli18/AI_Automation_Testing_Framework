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

