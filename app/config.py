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
    beta_base_url: str = os.getenv("BETA_BASE_URL", "http://localhost:3000")
    live_base_url: str = os.getenv("LIVE_BASE_URL", "http://localhost:3000")
    default_timeout_ms: int = int(os.getenv("DEFAULT_TIMEOUT", "30000"))
    screenshot_on_failure: bool = (
        os.getenv("SCREENSHOT_ON_FAILURE", "true").lower() == "true"
    )
    step_retry_max: int = int(os.getenv("STEP_RETRY_MAX", "2"))
    step_retry_delay_ms: int = int(os.getenv("STEP_RETRY_DELAY_MS", "400"))
    cors_allow_origins: str = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )

    @property
    def uploads_dir(self) -> Path:
        return self.storage_root / self.uploads_dir_name

    @property
    def runs_dir(self) -> Path:
        return self.storage_root / self.runs_dir_name


settings = Settings()

