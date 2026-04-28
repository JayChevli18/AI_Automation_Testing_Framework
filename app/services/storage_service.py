"""File-system storage service for uploads and runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.core.constants import RUN_STATUS_QUEUED
from app.core.exceptions import NotFoundError
from app.models.run_models import RunMeta, UploadedFileMeta


class StorageService:
    """Encapsulates all file-system storage operations."""

    def __init__(self) -> None:
        self.uploads_dir = settings.uploads_dir
        self.runs_dir = settings.runs_dir
        self._ensure_base_dirs()

    def _ensure_base_dirs(self) -> None:
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, file_bytes: bytes, filename: str) -> UploadedFileMeta:
        ext = Path(filename).suffix or ".xlsx"
        file_id = f"f_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
        stored_path = self.uploads_dir / f"{file_id}{ext}"
        stored_path.write_bytes(file_bytes)

        meta = UploadedFileMeta(
            file_id=file_id,
            filename=filename,
            stored_path=str(stored_path),
            uploaded_at=datetime.now(timezone.utc),
        )
        self._write_upload_meta(meta)
        return meta

    def create_run(
        self,
        file_id: str,
        environment: str,
        headless: bool,
        continue_on_failure: bool,
        step_timeout_ms: int,
        max_cases: int | None,
    ) -> RunMeta:
        upload_path = self._get_upload_path_by_file_id(file_id)
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:4]}"
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "logs").mkdir(exist_ok=True)
        (run_dir / "screenshots").mkdir(exist_ok=True)
        (run_dir / "html").mkdir(exist_ok=True)

        copied_path = run_dir / "input.xlsx"
        copied_path.write_bytes(upload_path.read_bytes())

        now = datetime.now(timezone.utc)
        run_meta = RunMeta(
            run_id=run_id,
            file_id=file_id,
            environment=environment,
            status=RUN_STATUS_QUEUED,
            headless=headless,
            continue_on_failure=continue_on_failure,
            step_timeout_ms=step_timeout_ms,
            max_cases=max_cases,
            created_at=now,
            updated_at=now,
        )
        self.write_json(run_id, "run_meta.json", run_meta.model_dump(mode="json"))
        return run_meta

    def update_run_status(self, run_id: str, status: str) -> RunMeta:
        run_meta = self.get_run_meta(run_id)
        run_meta.status = status
        run_meta.updated_at = datetime.now(timezone.utc)
        self.write_json(run_id, "run_meta.json", run_meta.model_dump(mode="json"))
        return run_meta

    def get_run_meta(self, run_id: str) -> RunMeta:
        run_meta_path = self.get_run_dir(run_id) / "run_meta.json"
        if not run_meta_path.exists():
            raise NotFoundError(f"Run metadata not found for run_id={run_id}")
        data = json.loads(run_meta_path.read_text(encoding="utf-8"))
        return RunMeta.model_validate(data)

    def get_run_dir(self, run_id: str) -> Path:
        run_dir = self.runs_dir / run_id
        if not run_dir.exists():
            raise NotFoundError(f"Run directory not found for run_id={run_id}")
        return run_dir

    def write_json(self, run_id: str, name: str, payload: dict | list) -> Path:
        run_dir = self.get_run_dir(run_id)
        path = run_dir / name
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def write_text(self, run_id: str, name: str, payload: str) -> Path:
        run_dir = self.get_run_dir(run_id)
        path = run_dir / name
        path.write_text(payload, encoding="utf-8")
        return path

    def _write_upload_meta(self, meta: UploadedFileMeta) -> None:
        meta_path = self.uploads_dir / f"{meta.file_id}.json"
        meta_path.write_text(
            json.dumps(meta.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

    def _get_upload_path_by_file_id(self, file_id: str) -> Path:
        candidates = list(self.uploads_dir.glob(f"{file_id}.*"))
        for candidate in candidates:
            if candidate.suffix.lower() in {".xlsx", ".xls"}:
                return candidate
        raise NotFoundError(f"Uploaded file not found for file_id={file_id}")

