"""FastAPI application bootstrap."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.test_routes import router as tests_router
from app.config import settings
from app.services.ollama_client import OllamaClient
from app.services.storage_service import StorageService

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(tests_router, prefix=settings.api_prefix)


@app.on_event("startup")
def on_startup() -> None:
    """Ensure required directories exist on startup."""
    StorageService()


@app.get("/health")
def health() -> dict[str, str | bool]:
    """Liveness and optional Ollama connectivity."""
    ollama_ok = OllamaClient().healthcheck()
    return {"status": "ok", "ollama_reachable": ollama_ok}

