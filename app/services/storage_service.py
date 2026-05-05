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
        allow_live_mutations: bool = False,
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
            allow_live_mutations=allow_live_mutations,
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

    def get_run_input_file(self, run_id: str) -> Path:
        """Return copied run input Excel path."""
        input_file = self.get_run_dir(run_id) / "input.xlsx"
        if not input_file.exists():
            raise NotFoundError(f"Run input.xlsx not found for run_id={run_id}")
        return input_file

    def write_json(self, run_id: str, name: str, payload: dict | list) -> Path:
        run_dir = self.get_run_dir(run_id)
        path = run_dir / name
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def read_json(self, run_id: str, name: str) -> dict | list:
        """Read a JSON artifact from the run directory."""
        path = self.get_run_dir(run_id) / name
        if not path.exists():
            raise NotFoundError(f"{name} not found for run_id={run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def write_text(self, run_id: str, name: str, payload: str) -> Path:
        run_dir = self.get_run_dir(run_id)
        path = run_dir / name
        path.write_text(payload, encoding="utf-8")
        return path

    def append_text(self, run_id: str, name: str, payload: str) -> Path:
        """Append plain text to a run artifact file."""
        run_dir = self.get_run_dir(run_id)
        path = run_dir / name
        with path.open("a", encoding="utf-8") as handle:
            handle.write(payload)
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

    def create_versioned_execution_dir(self, run_id: str) -> tuple[str, Path]:
        """Create executions/exec_<ts>_<id>/ with screenshots, html, allure-results."""
        run_dir = self.get_run_dir(run_id)
        executions_root = run_dir / "executions"
        executions_root.mkdir(exist_ok=True)
        execution_id = (
            f"exec_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:4]}"
        )
        exec_dir = executions_root / execution_id
        exec_dir.mkdir(parents=False, exist_ok=False)
        (exec_dir / "screenshots").mkdir(exist_ok=True)
        (exec_dir / "html").mkdir(exist_ok=True)
        (exec_dir / "allure-results").mkdir(exist_ok=True)
        return execution_id, exec_dir

    @staticmethod
    def _path_under_run(run_dir: Path, candidate: Path) -> Path:
        run_resolved = run_dir.resolve()
        path = (run_resolved / candidate).resolve()
        try:
            path.relative_to(run_resolved)
        except ValueError as exc:
            raise ValueError("Artifact path escapes run directory") from exc
        return path

    def write_json_relative(self, run_id: str, relative_path: str | Path, payload: dict | list) -> Path:
        """Write JSON under the run directory; creates parent folders."""
        run_dir = self.get_run_dir(run_id)
        path = self._path_under_run(run_dir, Path(relative_path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def read_json_relative(self, run_id: str, relative_path: str | Path) -> dict | list:
        run_dir = self.get_run_dir(run_id)
        path = self._path_under_run(run_dir, Path(relative_path))
        if not path.exists():
            raise NotFoundError(f"{relative_path} not found for run_id={run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def update_run_execution_options(
        self,
        run_id: str,
        *,
        environment: str | None = None,
        headless: bool | None = None,
        continue_on_failure: bool | None = None,
        step_timeout_ms: int | None = None,
        allow_live_mutations: bool | None = None,
    ) -> RunMeta:
        """Patch execution-related fields on run_meta without touching status."""
        meta = self.get_run_meta(run_id)
        updates: dict = {"updated_at": datetime.now(timezone.utc)}
        if environment is not None:
            updates["environment"] = environment
        if headless is not None:
            updates["headless"] = headless
        if continue_on_failure is not None:
            updates["continue_on_failure"] = continue_on_failure
        if step_timeout_ms is not None:
            updates["step_timeout_ms"] = step_timeout_ms
        if allow_live_mutations is not None:
            updates["allow_live_mutations"] = allow_live_mutations
        new_meta = meta.model_copy(update=updates)
        self.write_json(run_id, "run_meta.json", new_meta.model_dump(mode="json"))
        return new_meta

    def read_execution_manifest(self, run_id: str) -> list[dict]:
        run_dir = self.get_run_dir(run_id)
        path = run_dir / "executions" / "manifest.json"
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        return [x for x in raw if isinstance(x, dict)]

    def append_execution_manifest(self, run_id: str, entry: dict) -> None:
        run_dir = self.get_run_dir(run_id)
        manifest_path = run_dir / "executions" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        existing = self.read_execution_manifest(run_id)
        existing.append(entry)
        manifest_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    def write_latest_execution_pointer(self, run_id: str, execution_id: str) -> None:
        self.write_json_relative(
            run_id,
            Path("executions") / "latest.json",
            {"execution_id": execution_id},
        )

    def get_latest_execution_id(self, run_id: str) -> str | None:
        run_dir = self.get_run_dir(run_id)
        latest_path = run_dir / "executions" / "latest.json"
        if latest_path.exists():
            data = json.loads(latest_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("execution_id"):
                return str(data["execution_id"])
        manifest = self.read_execution_manifest(run_id)
        if manifest and manifest[-1].get("execution_id"):
            return str(manifest[-1]["execution_id"])
        return None

    def backup_interpreted_steps_if_exists(self, run_id: str) -> None:
        """Copy interpreted_steps.json to interpreted_steps.backup.<utc_ts>.json if present."""
        path = self.get_run_dir(run_id) / "interpreted_steps.json"
        if not path.exists():
            return
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup = path.with_name(f"interpreted_steps.backup.{ts}.json")
        backup.write_bytes(path.read_bytes())

    def atomic_write_interpreted_steps(self, run_id: str, payload: list[dict]) -> None:
        """Replace interpreted_steps.json via temp file + rename."""
        run_dir = self.get_run_dir(run_id)
        target = run_dir / "interpreted_steps.json"
        tmp = run_dir / "interpreted_steps.json.tmp"
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(target)

