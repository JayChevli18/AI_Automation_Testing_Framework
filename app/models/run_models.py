"""Domain models for runs and uploads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UploadedFileMeta(BaseModel):
    """Metadata for uploaded Excel files."""

    file_id: str
    filename: str
    stored_path: str
    uploaded_at: datetime


class RunMeta(BaseModel):
    """Lifecycle metadata for a test run."""

    run_id: str
    file_id: str
    environment: str
    status: str
    headless: bool
    continue_on_failure: bool
    step_timeout_ms: int
    max_cases: int | None
    allow_live_mutations: bool = False
    created_at: datetime
    updated_at: datetime

