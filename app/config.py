"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load variables from project .env for local development.
load_dotenv()


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
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    ollama_timeout_s: int = int(os.getenv("OLLAMA_TIMEOUT_S", "120"))
    ollama_json_format: bool = os.getenv("OLLAMA_JSON_FORMAT", "true").lower() == "true"

    @property
    def uploads_dir(self) -> Path:
        return self.storage_root / self.uploads_dir_name

    @property
    def runs_dir(self) -> Path:
        return self.storage_root / self.runs_dir_name


settings = Settings()

