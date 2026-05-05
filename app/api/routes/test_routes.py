"""Test execution related API routes."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import ValidationError

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logger import get_logger
from app.models.request_models import (
    CancelRunRequest,
    CleanupRunsRequest,
    ExecuteFromInterpretedRequest,
    InterpretRunRequest,
    InterpretedStepsPatchRequest,
    RunListRequest,
    RunRequest,
)
from app.models.response_models import (
    ArtifactIndexResponse,
    CancelRunResponse,
    CleanupRunsResponse,
    InterpretedStepsReadResponse,
    InterpretedStepsPatchResponse,
    LatestExecutionResponse,
    RunExecutionSummaryResponse,
    RunListData,
    RunListItem,
    RunListMeta,
    RunListPostResponse,
    RunListResponse,
    RunReportResponse,
    RunResponse,
    RunResultResponse,
    UploadResponse,
    VersionedExecutionResponse,
    VersionedExecutionsListResponse,
    VersionedExecutionSummaryResponse,
)
from app.services.run_manager import RunManager
from app.services.storage_service import StorageService

router = APIRouter(prefix="/tests", tags=["tests"])
logger = get_logger(__name__)

storage_service = StorageService()
run_manager = RunManager(storage_service=storage_service)


@router.post("/runs/list", response_model=RunListPostResponse)
def list_runs(body: RunListRequest) -> RunListPostResponse:
    """Paginated run listing with search/sort/filter (POST contract)."""
    try:
        runs, total_items = run_manager.list_runs_with_query(body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list runs: {exc}",
        ) from exc

    total_pages = (total_items + body.limit - 1) // body.limit if total_items > 0 else 0
    return RunListPostResponse(
        success=True,
        message="Run listing retrieved successfully",
        data=RunListData(
            list=[
                RunListItem(
                    run_id=r.run_id,
                    file_id=r.file_id,
                    status=r.status,
                    environment=r.environment,
                    created_at=r.created_at.isoformat(),
                    updated_at=r.updated_at.isoformat(),
                )
                for r in runs
            ],
            meta=RunListMeta(
                currentPage=body.page,
                totalPages=total_pages,
                totalItems=total_items,
                itemsPerPage=body.limit,
                hasNextPage=body.page < total_pages,
                hasPreviousPage=body.page > 1 and total_pages > 0,
            )
        ),
    )


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
    if request.environment == "live" and not request.allow_live_mutations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Runs against environment=live require allow_live_mutations=true "
                "(mutating steps are blocked by default for safety)."
            ),
        )
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


@router.post("/interpret", response_model=RunResponse)
def start_interpret_only(request: InterpretRunRequest) -> RunResponse:
    """Parse Excel, interpret steps with Ollama; does not open the browser.

    Use ``run_id`` from the response with ``POST /execute-versioned`` to run Playwright
    without calling the LLM again. Each browser run writes under
    ``executions/exec_<timestamp>_<id>/``.
    """
    try:
        logger.info("api=/interpret status=start file_id=%s", request.file_id)
        run_meta = run_manager.interpret_only(request)
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
            detail=f"Failed to interpret: {exc}",
        ) from exc

    logger.info("api=/interpret status=done run_id=%s", run_meta.run_id)
    return RunResponse(success=True, run_id=run_meta.run_id, status=run_meta.status)


@router.get(
    "/runs/{run_id}/interpreted-steps",
    response_model=InterpretedStepsReadResponse,
)
def get_interpreted_steps(run_id: str) -> InterpretedStepsReadResponse:
    """Return current interpreted_steps.json for editor/read-only UI."""
    try:
        interpreted_steps, revision = run_manager.get_interpreted_steps(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return InterpretedStepsReadResponse(
        success=True,
        run_id=run_id,
        interpreted_steps=interpreted_steps,
        revision=revision,
    )


@router.patch("/runs/{run_id}/interpreted-steps", response_model=InterpretedStepsPatchResponse)
def patch_interpreted_steps(run_id: str, body: InterpretedStepsPatchRequest) -> InterpretedStepsPatchResponse:
    """Merge manual edits into ``interpreted_steps.json`` without re-running the LLM.

    Send only the testcase(s) and step row(s) to change. Omit optional fields on a step
    patch to leave them unchanged; include ``interpreted`` or ``interpretation_error``
    with JSON ``null`` to clear them.
    """
    try:
        patched, revision = run_manager.patch_interpreted_steps(run_id, body)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(include_url=False),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to patch interpreted steps: {exc}",
        ) from exc

    logger.info("api=/runs/.../interpreted-steps run_id=%s patched=%s", run_id, patched)
    return InterpretedStepsPatchResponse(
        success=True,
        run_id=run_id,
        patched_test_case_ids=patched,
        revision=revision,
        message="interpreted_steps.json updated",
    )


@router.get("/runs/{run_id}/artifacts", response_model=ArtifactIndexResponse)
def get_artifact_index(run_id: str, execution_id: str | None = None) -> ArtifactIndexResponse:
    """Return consolidated artifact index for run or selected execution_id."""
    try:
        artifacts = run_manager.get_artifact_index(run_id, execution_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return ArtifactIndexResponse(
        success=True,
        run_id=run_id,
        execution_id=artifacts.get("execution_id"),
        artifacts=artifacts,
    )


@router.post("/runs/{run_id}/cancel", response_model=CancelRunResponse)
def cancel_run(run_id: str, body: CancelRunRequest) -> CancelRunResponse:
    """Request cooperative cancellation for a run."""
    try:
        meta = run_manager.request_cancel(run_id, reason=body.reason)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return CancelRunResponse(
        success=True,
        run_id=run_id,
        status=meta.status,
        message="Cancellation requested",
    )


@router.post("/runs/cleanup", response_model=CleanupRunsResponse)
def cleanup_runs(body: CleanupRunsRequest) -> CleanupRunsResponse:
    """Retention cleanup for old run folders."""
    try:
        deleted_ids, scanned = run_manager.cleanup_runs(body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {exc}",
        ) from exc
    return CleanupRunsResponse(
        success=True,
        message="Dry-run completed" if body.dry_run else "Cleanup completed",
        deleted_run_ids=deleted_ids,
        scanned=scanned,
    )


@router.post("/execute-versioned", response_model=VersionedExecutionResponse)
def start_execute_versioned(request: ExecuteFromInterpretedRequest) -> VersionedExecutionResponse:
    """Execute stored interpreted steps in the browser; artifacts are versioned per run."""
    if request.environment == "live" and not request.allow_live_mutations:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Runs against environment=live require allow_live_mutations=true "
                "(mutating steps are blocked by default for safety)."
            ),
        )
    try:
        logger.info(
            "api=/execute-versioned status=start interpret_run_id=%s",
            request.interpret_run_id,
        )
        execution_id, _summary = run_manager.execute_interpreted_versioned(request)
        run_meta = run_manager.get_run(request.interpret_run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute: {exc}",
        ) from exc

    logger.info(
        "api=/execute-versioned status=done run_id=%s execution_id=%s",
        run_meta.run_id,
        execution_id,
    )
    return VersionedExecutionResponse(
        success=True,
        run_id=run_meta.run_id,
        execution_id=execution_id,
        status=run_meta.status,
    )


@router.get("/runs/{run_id}/executions/latest", response_model=LatestExecutionResponse)
def get_latest_execution(run_id: str) -> LatestExecutionResponse:
    """Return latest versioned execution pointer + manifest entry."""
    try:
        _ = run_manager.get_run(run_id)  # ensure run exists
        execution_id, execution = run_manager.get_latest_execution_info(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return LatestExecutionResponse(
        success=True,
        run_id=run_id,
        execution_id=execution_id,
        execution=execution,
    )


@router.get("/versioned/{run_id}/executions", response_model=VersionedExecutionsListResponse)
def list_versioned_executions_for_run(run_id: str) -> VersionedExecutionsListResponse:
    """List versioned browser executions (see ``executions/manifest.json``)."""
    try:
        executions = run_manager.list_versioned_executions(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return VersionedExecutionsListResponse(
        success=True,
        run_id=run_id,
        executions=executions,
    )


@router.get(
    "/versioned/{run_id}/executions/{execution_id}/summary",
    response_model=VersionedExecutionSummaryResponse,
)
def get_versioned_execution_summary_api(run_id: str, execution_id: str) -> VersionedExecutionSummaryResponse:
    """Full execution summary for one versioned execution folder."""
    try:
        summary = run_manager.get_versioned_execution_summary(run_id, execution_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return VersionedExecutionSummaryResponse(
        success=True,
        run_id=run_id,
        execution_id=execution_id,
        summary=summary,
    )


@router.get(
    "/versioned/{run_id}/executions/{execution_id}/reports",
    response_model=RunReportResponse,
)
def get_versioned_report_artifacts(run_id: str, execution_id: str) -> RunReportResponse:
    """Report paths for a versioned execution (Allure + HTML under ``executions/<id>/``)."""
    try:
        report_index = run_manager.get_versioned_report_index(run_id, execution_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RunReportResponse(
        success=True,
        run_id=run_id,
        allure_results_dir=report_index["allure_results_dir"],
        allure_result_files=report_index["allure_result_files"],
        html_report_path=report_index["html_report_path"],
    )


@router.get("/versioned/{run_id}/executions/{execution_id}/report.html")
def get_versioned_report_html(run_id: str, execution_id: str) -> FileResponse:
    """Serve HTML dashboard for one versioned execution."""
    try:
        report_index = run_manager.get_versioned_report_index(run_id, execution_id)
        html_report_path = report_index["html_report_path"]
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FileResponse(
        path=html_report_path,
        media_type="text/html",
        filename=f"{run_id}_{execution_id}.html",
    )


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


@router.get("/results/{run_id}/summary", response_model=RunExecutionSummaryResponse)
def get_run_execution_summary(
    run_id: str,
    execution_id: str | None = None,
) -> RunExecutionSummaryResponse:
    """Return full per-step execution summary JSON."""
    try:
        summary = run_manager.get_execution_summary(run_id, execution_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return RunExecutionSummaryResponse(success=True, run_id=run_id, summary=summary)


@router.get("/reports/{run_id}", response_model=RunReportResponse)
def get_run_report_artifacts(
    run_id: str,
    execution_id: str | None = None,
) -> RunReportResponse:
    """Return report artifacts index for a completed run."""
    try:
        report_index = run_manager.get_report_index(run_id, execution_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RunReportResponse(
        success=True,
        run_id=run_id,
        allure_results_dir=report_index["allure_results_dir"],
        allure_result_files=report_index["allure_result_files"],
        html_report_path=report_index["html_report_path"],
    )


@router.get("/reports/{run_id}/html")
def get_run_report_html(
    run_id: str,
    execution_id: str | None = None,
) -> FileResponse:
    """Serve generated run HTML dashboard report."""
    try:
        report_index = run_manager.get_report_index(run_id, execution_id)
        html_report_path = report_index["html_report_path"]
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FileResponse(path=html_report_path, media_type="text/html", filename=f"{run_id}.html")

