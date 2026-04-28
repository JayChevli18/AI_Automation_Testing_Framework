"""Request payload models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    """Start run request payload."""

    file_id: str = Field(..., min_length=1)
    environment: Literal["beta", "live"] = "beta"
    headless: bool = True
    continue_on_failure: bool = True
    step_timeout_ms: int = Field(default=30000, ge=1000)
    max_cases: int | None = Field(default=None, ge=1)

