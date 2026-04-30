"""Test execution related API routes."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.exceptions import NotFoundError
from app.core.logger import get_logger
from app.models.request_models import RunRequest
from app.models.response_models import (
    RunCounts,
    RunResponse,
    RunResultResponse,
    UploadResponse,
)
from app.services.run_manager import RunManager
from app.services.storage_service import StorageService

router = APIRouter(prefix="/tests", tags=["tests"])
logger = get_logger(__name__)

storage_service = StorageService()
run_manager = RunManager(storage_service=storage_service)


@router.post("/upload", response_model=UploadResponse)
async def upload_test_file(file: UploadFile = File(...)) -> UploadResponse:
    """Upload Excel test case file and return file metadata."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.",
        )
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx/.xls files are supported.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    uploaded = storage_service.save_upload(file_bytes=file_bytes, filename=file.filename)
    return UploadResponse(
        success=True,
        file_id=uploaded.file_id,
        filename=uploaded.filename,
        stored_path=uploaded.stored_path,
    )


@router.post("/run", response_model=RunResponse)
def start_run(request: RunRequest) -> RunResponse:
    """Create run record and execute full v1 flow up to Playwright execution."""
    try:
        logger.info(
            "api=/run status=start file_id=%s environment=%s headless=%s continue_on_failure=%s",
            request.file_id,
            request.environment,
            request.headless,
            request.continue_on_failure,
        )
        run_meta = run_manager.create_run(request)
        run_manager.generate_normalized_testcases(run_meta.run_id)
        run_manager.generate_interpreted_steps(run_meta.run_id)
        run_manager.execute_interpreted_cases(run_meta.run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama is unavailable: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process run: {exc}",
        ) from exc

    run_meta = run_manager.get_run(run_meta.run_id)
    logger.info(
        "api=/run status=done run_id=%s final_status=%s",
        run_meta.run_id,
        run_meta.status,
    )
    return RunResponse(success=True, run_id=run_meta.run_id, status=run_meta.status)


@router.get("/results/{run_id}", response_model=RunResultResponse)
def get_run_results(run_id: str) -> RunResultResponse:
    """Return current run metadata and basic counters."""
    try:
        run_meta = run_manager.get_run(run_id)
        counts = run_manager.get_run_counts(run_id, run_meta.status)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RunResultResponse(
        success=True,
        run_id=run_meta.run_id,
        status=run_meta.status,
        counts=counts,
    )

