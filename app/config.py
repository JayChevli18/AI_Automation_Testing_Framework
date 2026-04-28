"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Environment-backed app settings."""

    app_name: str = os.getenv("APP_NAME", "AI Test Automation")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    api_prefix: str = os.getenv("API_PREFIX", "/api")
    storage_root: Path = Path(os.getenv("STORAGE_ROOT", "storage"))
    uploads_dir_name: str = os.getenv("UPLOADS_DIR_NAME", "uploads")
    runs_dir_name: str = os.getenv("RUNS_DIR_NAME", "runs")
    default_environment: str = os.getenv("DEFAULT_ENVIRONMENT", "beta")
    default_headless: bool = os.getenv("HEADLESS", "true").lower() == "true"
    step_timeout_ms: int = int(os.getenv("STEP_TIMEOUT_MS", "30000"))

    @property
    def uploads_dir(self) -> Path:
        return self.storage_root / self.uploads_dir_name

    @property
    def runs_dir(self) -> Path:
        return self.storage_root / self.runs_dir_name


settings = Settings()

