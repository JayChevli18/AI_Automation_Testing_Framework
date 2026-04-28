"""Run lifecycle orchestrator for API layer."""

from __future__ import annotations

from app.models.request_models import RunRequest
from app.models.run_models import RunMeta
from app.services.storage_service import StorageService


class RunManager:
    """Coordinates run metadata lifecycle for v1 foundation."""

    def __init__(self, storage_service: StorageService) -> None:
        self.storage_service = storage_service

    def create_run(self, request: RunRequest) -> RunMeta:
        return self.storage_service.create_run(
            file_id=request.file_id,
            environment=request.environment,
            headless=request.headless,
            continue_on_failure=request.continue_on_failure,
            step_timeout_ms=request.step_timeout_ms,
            max_cases=request.max_cases,
        )

    def get_run(self, run_id: str) -> RunMeta:
        return self.storage_service.get_run_meta(run_id)

