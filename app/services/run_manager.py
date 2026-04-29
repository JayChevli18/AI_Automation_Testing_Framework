"""Run lifecycle orchestrator for API layer."""

from __future__ import annotations

from app.core.constants import RUN_STATUS_FAILED, RUN_STATUS_INTERPRETED, RUN_STATUS_QUEUED
from app.models.interpreted_models import InterpretedCaseRecord, InterpretedStepRecord
from app.models.request_models import RunRequest
from app.models.run_models import RunMeta
from app.models.response_models import RunCounts
from app.models.testcase_models import NormalizedTestCase
from app.services.excel_parser import ExcelParser
from app.services.step_interpreter import StepInterpreter
from app.services.storage_service import StorageService
from app.services.testcase_normalizer import TestcaseNormalizer


class RunManager:
    """Coordinates run metadata lifecycle for v1 foundation."""

    def __init__(
        self,
        storage_service: StorageService,
        excel_parser: ExcelParser | None = None,
        testcase_normalizer: TestcaseNormalizer | None = None,
        step_interpreter: StepInterpreter | None = None,
    ) -> None:
        self.storage_service = storage_service
        self.excel_parser = excel_parser or ExcelParser()
        self.testcase_normalizer = testcase_normalizer or TestcaseNormalizer(
            parser=self.excel_parser
        )
        self.step_interpreter = step_interpreter or StepInterpreter()

    def create_run(self, request: RunRequest) -> RunMeta:
        return self.storage_service.create_run(
            file_id=request.file_id,
            environment=request.environment,
            headless=request.headless,
            continue_on_failure=request.continue_on_failure,
            step_timeout_ms=request.step_timeout_ms,
            max_cases=request.max_cases,
        )

    def get_run(self, run_id: str) -> RunMeta:
        return self.storage_service.get_run_meta(run_id)

    def get_run_counts(self, run_id: str, status: str) -> RunCounts:
        """Return lightweight case counts based on normalized artifacts."""
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
        input_path = self.storage_service.get_run_input_file(run_id)
        raw_rows = self.excel_parser.parse_excel(input_path)
        normalized_cases = self.testcase_normalizer.normalize(raw_rows)

        self.storage_service.write_json(
            run_id=run_id,
            name="normalized_testcases.json",
            payload=[case.model_dump(mode="json") for case in normalized_cases],
        )
        return normalized_cases

    def generate_interpreted_steps(self, run_id: str) -> list[InterpretedCaseRecord]:
        """Call Ollama per step and persist interpreted_steps.json."""
        raw = self.storage_service.read_json(run_id, "normalized_testcases.json")
        if not isinstance(raw, list):
            raise ValueError("normalized_testcases.json must be a list")

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

        if success_count == 0 and failed_count > 0 and first_connection_error:
            self.storage_service.update_run_status(run_id, RUN_STATUS_FAILED)
            raise ConnectionError(first_connection_error)

        self.storage_service.update_run_status(run_id, RUN_STATUS_INTERPRETED)
        return cases_out

