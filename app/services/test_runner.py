"""Playwright runner for executing interpreted testcases."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from playwright.async_api import async_playwright

from app.config import settings
from app.models.execution_models import CaseExecutionResult, RunExecutionSummary
from app.models.interpreted_models import InterpretedCaseRecord
from app.models.run_models import RunMeta
from app.models.testcase_models import NormalizedTestCase
from app.services.action_executor import ActionExecutor
from app.services.selector_cache import SelectorCache


class TestRunner:
    """Execute interpreted testcases and produce run execution summary."""

    def __init__(self, action_executor: ActionExecutor | None = None) -> None:
        self.action_executor = action_executor or ActionExecutor()

    async def run(
        self,
        run_meta: RunMeta,
        cases: list[NormalizedTestCase],
        interpreted_cases: list[InterpretedCaseRecord],
        run_dir: Path,
        run_logger: Callable[[str, str], None] | None = None,
        *,
        artifact_base_dir: Path | None = None,
    ) -> RunExecutionSummary:
        case_map = {c.test_case_id: c for c in cases}
        interpreted_map = {c.test_case_id: c for c in interpreted_cases}
        results: list[CaseExecutionResult] = []
        passed = 0
        failed = 0

        artifact_root = artifact_base_dir if artifact_base_dir is not None else run_dir
        screenshots_dir = artifact_root / "screenshots"
        html_dir = artifact_root / "html"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        html_dir.mkdir(parents=True, exist_ok=True)
        step_timeout = run_meta.step_timeout_ms or settings.default_timeout_ms

        async with async_playwright() as p:
            for test_case_id, case in case_map.items():
                if run_logger:
                    run_logger(
                        run_meta.run_id,
                        f"phase=execute testcase={test_case_id} status=start steps={len(case.steps)}",
                    )
                interpreted = interpreted_map.get(test_case_id)
                if not interpreted:
                    results.append(
                        CaseExecutionResult(
                            test_case_id=test_case_id,
                            test_case_name=case.test_case_name,
                            module=case.module,
                            status="failed",
                            steps=[],
                        )
                    )
                    failed += 1
                    if run_logger:
                        run_logger(
                            run_meta.run_id,
                            f"phase=execute testcase={test_case_id} status=failed reason=missing_interpreted_case",
                        )
                    continue

                browser = await p.chromium.launch(headless=run_meta.headless)
                context = await browser.new_context()
                page = await context.new_page()
                page.set_default_timeout(step_timeout)
                if run_logger:
                    run_logger(
                        run_meta.run_id,
                        f"phase=execute testcase={test_case_id} browser=chromium mode={'headless' if run_meta.headless else 'headed'} launched=true",
                    )

                step_results = []
                case_status = "passed"
                selector_cache = SelectorCache()
                base_url = (
                    settings.live_base_url
                    if run_meta.environment == "live"
                    else settings.beta_base_url
                )
                for step in interpreted.steps:
                    step_result = await self.action_executor.execute_step(
                        page=page,
                        step_record=step,
                        test_data=case.test_data,
                        run_id=run_meta.run_id,
                        test_case_id=test_case_id,
                        screenshots_dir=screenshots_dir,
                        html_dir=html_dir,
                        timeout_ms=step_timeout,
                        environment=run_meta.environment,
                        allow_live_mutations=run_meta.allow_live_mutations,
                        base_url=base_url,
                        selector_cache=selector_cache,
                    )
                    step_results.append(step_result)
                    if step_result.status == "failed":
                        case_status = "failed"
                        if run_logger:
                            run_logger(
                                run_meta.run_id,
                                f"phase=execute testcase={test_case_id} step={step_result.step_index} status=failed error={step_result.error_message}",
                            )
                        if not run_meta.continue_on_failure:
                            break

                await context.close()
                await browser.close()

                results.append(
                    CaseExecutionResult(
                        test_case_id=test_case_id,
                        test_case_name=case.test_case_name,
                        module=case.module,
                        status=case_status,
                        steps=step_results,
                    )
                )
                if case_status == "passed":
                    passed += 1
                else:
                    failed += 1
                if run_logger:
                    run_logger(
                        run_meta.run_id,
                        f"phase=execute testcase={test_case_id} status={case_status}",
                    )

        return RunExecutionSummary(
            run_id=run_meta.run_id,
            status="completed" if failed == 0 else "failed",
            total_cases=len(results),
            passed_cases=passed,
            failed_cases=failed,
            skipped_cases=0,
            running_cases=0,
            pending_cases=0,
            cases=results,
        )

