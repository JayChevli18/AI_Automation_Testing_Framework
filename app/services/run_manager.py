"""Run lifecycle orchestrator for API layer."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.constants import (
    RUN_STATUS_CANCELLED,
    RUN_STATUS_COMPLETED,
    RUN_STATUS_FAILED,
    RUN_STATUS_INTERPRETED,
    RUN_STATUS_QUEUED,
    RUN_STATUS_RUNNING,
)
from app.core.exceptions import ConflictError
from app.core.logger import get_logger
from app.models.execution_models import RunExecutionSummary
from app.models.interpreted_models import InterpretedCaseRecord, InterpretedStepRecord
from app.models.request_models import (
    CleanupRunsRequest,
    ExecuteFromInterpretedRequest,
    InterpretRunRequest,
    InterpretedStepsPatchRequest,
    RunListRequest,
    RunRequest,
    StepPatchItem,
)
from app.models.run_models import RunMeta
from app.models.response_models import RunCounts
from app.models.testcase_models import NormalizedTestCase
from app.services.excel_parser import ExcelParser
from app.services.step_interpreter import StepInterpreter
from app.services.storage_service import StorageService
from app.services.test_runner import TestRunner
from app.services.testcase_normalizer import TestcaseNormalizer
from app.services.report_service import ReportService
from app.utils.listing_utils import apply_listing_query


class RunManager:
    """Coordinates run metadata lifecycle for v1 foundation."""

    def __init__(
        self,
        storage_service: StorageService,
        excel_parser: ExcelParser | None = None,
        testcase_normalizer: TestcaseNormalizer | None = None,
        step_interpreter: StepInterpreter | None = None,
        test_runner: TestRunner | None = None,
        report_service: ReportService | None = None,
    ) -> None:
        self.logger = get_logger(__name__)
        self.storage_service = storage_service
        self.excel_parser = excel_parser or ExcelParser()
        self.testcase_normalizer = testcase_normalizer or TestcaseNormalizer(
            parser=self.excel_parser
        )
        self.step_interpreter = step_interpreter or StepInterpreter()
        self.test_runner = test_runner or TestRunner()
        self.report_service = report_service or ReportService()

    def _log(self, run_id: str, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        line = f"{timestamp} | {message}\n"
        self.logger.info("run_id=%s | %s", run_id, message)
        self.storage_service.append_text(run_id, "logs/run.log", line)

    def create_run(self, request: RunRequest) -> RunMeta:
        return self.storage_service.create_run(
            file_id=request.file_id,
            environment=request.environment,
            headless=request.headless,
            continue_on_failure=request.continue_on_failure,
            step_timeout_ms=request.step_timeout_ms,
            max_cases=request.max_cases,
            allow_live_mutations=request.allow_live_mutations,
        )

    def get_run(self, run_id: str) -> RunMeta:
        return self.storage_service.get_run_meta(run_id)

    def list_runs(self, limit: int = 50) -> list[RunMeta]:
        """Return run metadata rows for list UIs."""
        return self.storage_service.list_run_metas(limit=limit)

    @staticmethod
    def _field_value(run: RunMeta, field: str) -> object:
        return getattr(run, field)

    def list_runs_with_query(self, query: RunListRequest) -> tuple[list[RunMeta], int]:
        """Run listing with filter/search/sort and pagination."""
        rows = self.storage_service.list_run_metas(limit=5000)
        return apply_listing_query(
            rows,
            page=query.page,
            limit=query.limit,
            search=query.search,
            search_getters=[
                lambda r: r.run_id,
                lambda r: r.file_id,
                lambda r: r.status,
                lambda r: r.environment,
            ],
            filters=query.filters,
            sort_by=query.sortingOptions.sortBy,
            sort_order=query.sortingOptions.sortOrder,
            value_getter=self._field_value,
            datetime_fields={"created_at", "updated_at"},
        )

    @staticmethod
    def _apply_case_limit(items: list, max_cases: int | None) -> list:
        if max_cases is None or max_cases <= 0:
            return items
        return items[:max_cases]

    def get_run_counts(self, run_id: str, status: str) -> RunCounts:
        """Return lightweight case counts based on normalized artifacts."""
        try:
            execution_summary = self.storage_service.read_json(run_id, "execution_summary.json")
            if isinstance(execution_summary, dict):
                return RunCounts(
                    total_cases=int(execution_summary.get("total_cases", 0)),
                    passed_cases=int(execution_summary.get("passed_cases", 0)),
                    failed_cases=int(execution_summary.get("failed_cases", 0)),
                    skipped_cases=int(execution_summary.get("skipped_cases", 0)),
                    running_cases=int(execution_summary.get("running_cases", 0)),
                    pending_cases=int(execution_summary.get("pending_cases", 0)),
                )
        except Exception:
            pass

        try:
            latest_execution_id = self.storage_service.get_latest_execution_id(run_id)
            if latest_execution_id:
                rel = Path("executions") / latest_execution_id / "execution_summary.json"
                execution_summary = self.storage_service.read_json_relative(run_id, rel)
                if isinstance(execution_summary, dict):
                    return RunCounts(
                        total_cases=int(execution_summary.get("total_cases", 0)),
                        passed_cases=int(execution_summary.get("passed_cases", 0)),
                        failed_cases=int(execution_summary.get("failed_cases", 0)),
                        skipped_cases=int(execution_summary.get("skipped_cases", 0)),
                        running_cases=int(execution_summary.get("running_cases", 0)),
                        pending_cases=int(execution_summary.get("pending_cases", 0)),
                    )
        except Exception:
            pass

        try:
            normalized = self.storage_service.read_json(run_id, "normalized_testcases.json")
            total_cases = len(normalized) if isinstance(normalized, list) else 0
        except Exception:
            total_cases = 0

        pending_cases = total_cases if status in (RUN_STATUS_QUEUED, RUN_STATUS_INTERPRETED) else 0
        return RunCounts(
            total_cases=total_cases,
            passed_cases=0,
            failed_cases=0,
            skipped_cases=0,
            running_cases=0,
            pending_cases=pending_cases,
        )

    def generate_normalized_testcases(self, run_id: str) -> list[NormalizedTestCase]:
        """Parse run input Excel and persist normalized testcase JSON."""
        self._log(run_id, "phase=normalize status=start")
        input_path = self.storage_service.get_run_input_file(run_id)
        raw_rows = self.excel_parser.parse_excel(input_path)
        normalized_cases = self.testcase_normalizer.normalize(raw_rows)
        run_meta = self.get_run(run_id)
        normalized_cases = self._apply_case_limit(normalized_cases, run_meta.max_cases)

        self.storage_service.write_json(
            run_id=run_id,
            name="normalized_testcases.json",
            payload=[case.model_dump(mode="json") for case in normalized_cases],
        )
        self._log(
            run_id,
            f"phase=normalize status=done total_raw_rows={len(raw_rows)} total_cases={len(normalized_cases)}",
        )
        return normalized_cases

    def generate_interpreted_steps(self, run_id: str) -> list[InterpretedCaseRecord]:
        """Call Ollama per step and persist interpreted_steps.json."""
        self._log(run_id, "phase=interpret status=start")
        raw = self.storage_service.read_json(run_id, "normalized_testcases.json")
        if not isinstance(raw, list):
            raise ValueError("normalized_testcases.json must be a list")
        run_meta = self.get_run(run_id)
        raw = self._apply_case_limit(raw, run_meta.max_cases)

        cases_out: list[InterpretedCaseRecord] = []
        success_count = 0
        failed_count = 0
        first_connection_error: str | None = None
        for item in raw:
            case = NormalizedTestCase.model_validate(item)
            step_records: list[InterpretedStepRecord] = []
            for idx, step_text in enumerate(case.steps):
                interpreted, err = self.step_interpreter.try_interpret_step(
                    step_text, case.test_data
                )
                if interpreted is not None:
                    success_count += 1
                else:
                    failed_count += 1
                    if err and "Ollama request failed" in err and first_connection_error is None:
                        first_connection_error = err
                rec = InterpretedStepRecord(
                    step_index=idx,
                    raw_step=step_text,
                    interpreted=interpreted,
                    interpretation_error=(
                        {
                            "error_type": "INTERPRETATION_ERROR",
                            "error_message": err,
                        }
                        if err
                        else None
                    ),
                )
                step_records.append(rec)
            cases_out.append(
                InterpretedCaseRecord(
                    test_case_id=case.test_case_id,
                    test_case_name=case.test_case_name,
                    module=case.module,
                    steps=step_records,
                )
            )

        self.storage_service.write_json(
            run_id=run_id,
            name="interpreted_steps.json",
            payload=[c.model_dump(mode="json") for c in cases_out],
        )
        self.storage_service.set_interpreted_revision(run_id, 1)
        self._log(
            run_id,
            f"phase=interpret status=done interpreted_steps={success_count} failed_steps={failed_count}",
        )

        if success_count == 0 and failed_count > 0 and first_connection_error:
            self.storage_service.update_run_status(run_id, RUN_STATUS_FAILED)
            self._log(run_id, f"phase=interpret status=failed reason={first_connection_error}")
            raise ConnectionError(first_connection_error)

        self.storage_service.update_run_status(run_id, RUN_STATUS_INTERPRETED)
        return cases_out

    def execute_interpreted_cases(self, run_id: str) -> RunExecutionSummary:
        """Execute interpreted steps via Playwright and persist summary."""
        self.storage_service.update_run_status(run_id, RUN_STATUS_RUNNING)
        run_meta = self.storage_service.get_run_meta(run_id)
        self._log(
            run_id,
            f"phase=execute status=start environment={run_meta.environment} headless={run_meta.headless}",
        )

        normalized_raw = self.storage_service.read_json(run_id, "normalized_testcases.json")
        interpreted_raw = self.storage_service.read_json(run_id, "interpreted_steps.json")
        if not isinstance(normalized_raw, list) or not isinstance(interpreted_raw, list):
            self.storage_service.update_run_status(run_id, RUN_STATUS_FAILED)
            raise ValueError("normalized/interpreted artifacts must be list JSON structures.")

        normalized_cases = [NormalizedTestCase.model_validate(i) for i in normalized_raw]
        interpreted_cases = [InterpretedCaseRecord.model_validate(i) for i in interpreted_raw]
        normalized_cases = self._apply_case_limit(normalized_cases, run_meta.max_cases)
        interpreted_cases = self._apply_case_limit(interpreted_cases, run_meta.max_cases)
        run_dir = self.storage_service.get_run_dir(run_id)

        summary = asyncio.run(
            self.test_runner.run(
                run_meta=run_meta,
                cases=normalized_cases,
                interpreted_cases=interpreted_cases,
                run_dir=run_dir,
                run_logger=self._log,
                should_cancel=lambda: self.storage_service.is_cancel_requested(run_id),
            )
        )
        self.storage_service.write_json(
            run_id=run_id,
            name="execution_summary.json",
            payload=summary.model_dump(mode="json"),
        )
        allure_dir = self.report_service.write_allure_results(run_dir=run_dir, summary=summary)
        html_report = self.report_service.write_html_report(run_dir=run_dir, summary=summary)
        self._log(
            run_id,
            f"phase=report status=done allure_results_dir={allure_dir} html_report={html_report}",
        )
        if summary.status == "cancelled":
            final_status = RUN_STATUS_CANCELLED
        else:
            final_status = RUN_STATUS_COMPLETED if summary.failed_cases == 0 else RUN_STATUS_FAILED
        self.storage_service.update_run_status(run_id, final_status)
        self._log(
            run_id,
            f"phase=execute status=done total_cases={summary.total_cases} passed={summary.passed_cases} failed={summary.failed_cases}",
        )
        return summary

    def get_execution_summary(self, run_id: str, execution_id: str | None = None) -> dict:
        """Return persisted full execution summary JSON."""
        if execution_id:
            return self.get_versioned_execution_summary(run_id, execution_id)
        try:
            raw = self.storage_service.read_json(run_id, "execution_summary.json")
            if not isinstance(raw, dict):
                raise ValueError("execution_summary.json must be an object")
            return raw
        except Exception:
            latest_execution_id = self.storage_service.get_latest_execution_id(run_id)
            if not latest_execution_id:
                raise
            rel = Path("executions") / latest_execution_id / "execution_summary.json"
            raw = self.storage_service.read_json_relative(run_id, rel)
            if not isinstance(raw, dict):
                raise ValueError("execution_summary.json must be an object")
            return raw

    def get_report_index(self, run_id: str, execution_id: str | None = None) -> dict:
        """Return report artifact locations for a run."""
        if execution_id:
            return self.get_versioned_report_index(run_id, execution_id)
        run_dir = self.storage_service.get_run_dir(run_id)
        allure_dir = run_dir / "allure-results"
        if allure_dir.exists():
            result_files = sorted(p.name for p in allure_dir.glob("*-result.json"))
            return {
                "allure_results_dir": str(allure_dir),
                "allure_result_files": result_files,
                "html_report_path": str(run_dir / "report.html"),
            }
        latest_execution_id = self.storage_service.get_latest_execution_id(run_id)
        if not latest_execution_id:
            raise FileNotFoundError("allure-results not found for this run")
        return self.get_versioned_report_index(run_id, latest_execution_id)

    def get_interpreted_steps(self, run_id: str) -> tuple[list[dict], int]:
        """Return interpreted_steps.json payload."""
        raw = self.storage_service.read_json(run_id, "interpreted_steps.json")
        if not isinstance(raw, list):
            raise ValueError("interpreted_steps.json must be a JSON array")
        return raw, self.storage_service.get_interpreted_revision(run_id)

    def get_latest_execution_info(self, run_id: str) -> tuple[str | None, dict | None]:
        """Return latest execution id and manifest entry."""
        entry = self.storage_service.get_latest_execution_entry(run_id)
        if not entry:
            return None, None
        execution_id = entry.get("execution_id")
        return (str(execution_id) if execution_id else None, entry)

    def get_artifact_index(self, run_id: str, execution_id: str | None = None) -> dict:
        """Return a consolidated artifact index for UI evidence rendering."""
        run_dir = self.storage_service.get_run_dir(run_id)
        target_execution_id = execution_id
        base_dir = run_dir
        if target_execution_id is None:
            target_execution_id = self.storage_service.get_latest_execution_id(run_id)
        if target_execution_id:
            base_dir = run_dir / "executions" / target_execution_id

        report_index = self.get_report_index(run_id, target_execution_id)
        screenshots = sorted(str(p) for p in (base_dir / "screenshots").glob("*.png"))
        html_dumps = sorted(str(p) for p in (base_dir / "html").glob("*.html"))
        summary_path = base_dir / "execution_summary.json"

        return {
            "execution_id": target_execution_id,
            "report": report_index,
            "summary_path": str(summary_path) if summary_path.exists() else None,
            "screenshots": screenshots,
            "html_dumps": html_dumps,
        }

    def interpret_only(self, request: InterpretRunRequest) -> RunMeta:
        """Create run folder, normalize Excel, interpret steps with LLM; no browser."""
        run_meta = self.create_run(request)
        self.generate_normalized_testcases(run_meta.run_id)
        self.generate_interpreted_steps(run_meta.run_id)
        return self.get_run(run_meta.run_id)

    def execute_interpreted_versioned(
        self, request: ExecuteFromInterpretedRequest
    ) -> tuple[str, RunExecutionSummary]:
        """Run Playwright using existing interpreted JSON; artifacts under executions/<id>/."""
        run_id = request.interpret_run_id
        run_dir = self.storage_service.get_run_dir(run_id)
        if not (run_dir / "interpreted_steps.json").exists():
            raise ValueError(
                "interpreted_steps.json not found; call POST /interpret (or full /run) first."
            )
        if not (run_dir / "normalized_testcases.json").exists():
            raise ValueError("normalized_testcases.json not found for this run_id.")

        self.storage_service.update_run_execution_options(
            run_id,
            environment=request.environment,
            headless=request.headless,
            continue_on_failure=request.continue_on_failure,
            step_timeout_ms=request.step_timeout_ms,
            allow_live_mutations=request.allow_live_mutations,
        )

        execution_id, execution_dir = self.storage_service.create_versioned_execution_dir(run_id)
        started_at = datetime.now(timezone.utc)
        self.storage_service.update_run_status(run_id, RUN_STATUS_RUNNING)
        run_meta = self.storage_service.get_run_meta(run_id)
        self._log(
            run_id,
            f"phase=execute_versioned execution_id={execution_id} status=start "
            f"environment={run_meta.environment} headless={run_meta.headless}",
        )

        normalized_raw = self.storage_service.read_json(run_id, "normalized_testcases.json")
        interpreted_raw = self.storage_service.read_json(run_id, "interpreted_steps.json")
        if not isinstance(normalized_raw, list) or not isinstance(interpreted_raw, list):
            self.storage_service.update_run_status(run_id, RUN_STATUS_FAILED)
            raise ValueError("normalized/interpreted artifacts must be list JSON structures.")

        normalized_cases = [NormalizedTestCase.model_validate(i) for i in normalized_raw]
        interpreted_cases = [InterpretedCaseRecord.model_validate(i) for i in interpreted_raw]
        normalized_cases = self._apply_case_limit(normalized_cases, run_meta.max_cases)
        interpreted_cases = self._apply_case_limit(interpreted_cases, run_meta.max_cases)

        try:
            summary = asyncio.run(
                self.test_runner.run(
                    run_meta=run_meta,
                    cases=normalized_cases,
                    interpreted_cases=interpreted_cases,
                    run_dir=run_dir,
                    run_logger=self._log,
                    should_cancel=lambda: self.storage_service.is_cancel_requested(run_id),
                    artifact_base_dir=execution_dir,
                )
            )
        except Exception as exc:
            self.storage_service.update_run_status(run_id, RUN_STATUS_FAILED)
            finished_bad = datetime.now(timezone.utc)
            self.storage_service.append_execution_manifest(
                run_id,
                {
                    "execution_id": execution_id,
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_bad.isoformat(),
                    "status": "failed",
                    "error_message": str(exc),
                },
            )
            self._log(
                run_id,
                f"phase=execute_versioned execution_id={execution_id} status=error error={exc}",
            )
            raise

        rel_summary = Path("executions") / execution_id / "execution_summary.json"
        self.storage_service.write_json_relative(
            run_id,
            rel_summary,
            summary.model_dump(mode="json"),
        )
        allure_dir = self.report_service.write_allure_results(run_dir=execution_dir, summary=summary)
        html_report = self.report_service.write_html_report(run_dir=execution_dir, summary=summary)
        finished_at = datetime.now(timezone.utc)

        self.storage_service.append_execution_manifest(
            run_id,
            {
                "execution_id": execution_id,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "status": summary.status,
                "total_cases": summary.total_cases,
                "passed_cases": summary.passed_cases,
                "failed_cases": summary.failed_cases,
            },
        )
        self.storage_service.write_latest_execution_pointer(run_id, execution_id)

        if summary.status == "cancelled":
            final_status = RUN_STATUS_CANCELLED
        else:
            final_status = RUN_STATUS_COMPLETED if summary.failed_cases == 0 else RUN_STATUS_FAILED
        self.storage_service.update_run_status(run_id, final_status)
        self._log(
            run_id,
            f"phase=execute_versioned execution_id={execution_id} status=done "
            f"allure_results_dir={allure_dir} html_report={html_report} "
            f"passed={summary.passed_cases} failed={summary.failed_cases}",
        )
        return execution_id, summary

    def list_versioned_executions(self, run_id: str) -> list[dict]:
        """Return manifest entries for versioned browser executions."""
        return self.storage_service.read_execution_manifest(run_id)

    def get_versioned_execution_summary(self, run_id: str, execution_id: str) -> dict:
        rel = Path("executions") / execution_id / "execution_summary.json"
        raw = self.storage_service.read_json_relative(run_id, rel)
        if not isinstance(raw, dict):
            raise ValueError("execution_summary must be an object")
        return raw

    def get_versioned_report_index(self, run_id: str, execution_id: str) -> dict:
        run_dir = self.storage_service.get_run_dir(run_id)
        execution_dir = run_dir / "executions" / execution_id
        allure_dir = execution_dir / "allure-results"
        if not allure_dir.exists():
            raise FileNotFoundError(f"allure-results not found for execution_id={execution_id}")
        result_files = sorted(p.name for p in allure_dir.glob("*-result.json"))
        return {
            "allure_results_dir": str(allure_dir),
            "allure_result_files": result_files,
            "html_report_path": str(execution_dir / "report.html"),
        }

    @staticmethod
    def _merge_step_record(record: InterpretedStepRecord, patch: StepPatchItem) -> InterpretedStepRecord:
        data = record.model_dump(mode="json")
        if "raw_step" in patch.model_fields_set:
            data["raw_step"] = patch.raw_step
        if "interpreted" in patch.model_fields_set:
            if patch.interpreted is None:
                data["interpreted"] = None
            else:
                data["interpreted"] = patch.interpreted.model_dump(mode="json")
        if "interpretation_error" in patch.model_fields_set:
            data["interpretation_error"] = patch.interpretation_error
        return InterpretedStepRecord.model_validate(data)

    def patch_interpreted_steps(
        self, run_id: str, request: InterpretedStepsPatchRequest
    ) -> tuple[list[str], int]:
        """Merge PATCH payload into interpreted_steps.json (validated, atomic write)."""
        meta = self.get_run(run_id)
        if meta.status == RUN_STATUS_RUNNING:
            raise ConflictError(
                "Run status is 'running'; wait until execution finishes before editing interpreted steps."
            )
        current_revision = self.storage_service.get_interpreted_revision(run_id)
        if request.expected_revision is not None and request.expected_revision != current_revision:
            raise ConflictError(
                f"Revision mismatch. expected={request.expected_revision}, current={current_revision}"
            )

        raw = self.storage_service.read_json(run_id, "interpreted_steps.json")
        if not isinstance(raw, list):
            raise ValueError("interpreted_steps.json must be a JSON array")

        cases = [InterpretedCaseRecord.model_validate(x) for x in raw]
        by_id = {c.test_case_id: i for i, c in enumerate(cases)}
        patched_ids: list[str] = []

        for patch in request.patches:
            if patch.test_case_id not in by_id:
                raise ValueError(f"Unknown test_case_id: {patch.test_case_id!r}")
            idx = by_id[patch.test_case_id]
            case = cases[idx]

            if patch.steps is not None:
                cases[idx] = InterpretedCaseRecord(
                    test_case_id=case.test_case_id,
                    test_case_name=case.test_case_name,
                    module=case.module,
                    steps=patch.steps,
                )
            else:
                new_steps = list(case.steps)
                for sp in patch.step_patches or []:
                    matches = [i for i, s in enumerate(new_steps) if s.step_index == sp.step_index]
                    if not matches:
                        raise ValueError(
                            f"No step with step_index={sp.step_index} for {patch.test_case_id!r}"
                        )
                    pos = matches[0]
                    new_steps[pos] = self._merge_step_record(new_steps[pos], sp)
                cases[idx] = case.model_copy(update={"steps": new_steps})

            patched_ids.append(patch.test_case_id)

        payload = [c.model_dump(mode="json") for c in cases]

        self.storage_service.backup_interpreted_steps_if_exists(run_id)
        self.storage_service.atomic_write_interpreted_steps(run_id, payload)
        next_revision = max(1, current_revision) + 1
        self.storage_service.set_interpreted_revision(run_id, next_revision)
        self._log(
            run_id,
            f"interpreted_steps.json patched test_cases={patched_ids} revision={next_revision}",
        )
        return patched_ids, next_revision

    def request_cancel(self, run_id: str, reason: str | None = None) -> RunMeta:
        """Request cancellation for a run."""
        meta = self.get_run(run_id)
        if meta.status not in {RUN_STATUS_RUNNING, RUN_STATUS_QUEUED, RUN_STATUS_INTERPRETED}:
            return meta
        updated = self.storage_service.request_cancel_run(run_id)
        self._log(
            run_id,
            f"phase=cancel status=requested reason={reason or 'user_requested'}",
        )
        return updated

    def cleanup_runs(self, request: CleanupRunsRequest) -> tuple[list[str], int]:
        """Delete old non-running runs based on retention policy."""
        all_runs = self.storage_service.list_run_metas(limit=10000)
        cutoff = datetime.now(timezone.utc) - timedelta(days=request.retain_days)
        candidates = [
            r
            for r in all_runs
            if r.updated_at < cutoff
            and r.status not in {RUN_STATUS_RUNNING, RUN_STATUS_QUEUED}
        ]
        candidates = candidates[: request.max_delete]
        deleted_ids: list[str] = []
        if not request.dry_run:
            for run in candidates:
                self.storage_service.delete_run_dir(run.run_id)
                deleted_ids.append(run.run_id)
        else:
            deleted_ids = [r.run_id for r in candidates]
        return deleted_ids, len(all_runs)

