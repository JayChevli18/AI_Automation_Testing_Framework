"""FastAPI application bootstrap."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.test_routes import router as tests_router
from app.config import settings
from app.services.ollama_client import OllamaClient
from app.services.storage_service import StorageService

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(tests_router, prefix=settings.api_prefix)

_cors_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


def _error_envelope(request: Request, code: str, message: str, details=None):
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": getattr(request.state, "request_id", None),
        },
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = f"HTTP_{exc.status_code}"
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_envelope(request, code, str(exc.detail)),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=_error_envelope(request, "INTERNAL_SERVER_ERROR", str(exc)),
    )


@app.on_event("startup")
def on_startup() -> None:
    """Ensure required directories exist on startup."""
    StorageService()


@app.get("/health")
def health() -> dict[str, str | bool]:
    """Liveness and optional Ollama connectivity."""
    ollama_ok = OllamaClient().healthcheck()
    return {"status": "ok", "ollama_reachable": ollama_ok}

