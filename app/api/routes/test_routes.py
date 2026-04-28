"""Test execution related API routes."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.exceptions import NotFoundError
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
    """Create a run record and queue run lifecycle."""
    try:
        run_meta = run_manager.create_run(request)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RunResponse(success=True, run_id=run_meta.run_id, status=run_meta.status)


@router.get("/results/{run_id}", response_model=RunResultResponse)
def get_run_results(run_id: str) -> RunResultResponse:
    """Return current run metadata and basic counters."""
    try:
        run_meta = run_manager.get_run(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RunResultResponse(
        success=True,
        run_id=run_meta.run_id,
        status=run_meta.status,
        counts=RunCounts(),
    )

