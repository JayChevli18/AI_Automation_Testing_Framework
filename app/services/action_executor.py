"""Execute interpreted actions against a Playwright page."""

from __future__ import annotations

import time
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, expect

from app.config import settings
from app.models.execution_models import StepExecutionResult
from app.models.interpreted_models import InterpretedStepRecord
from app.services.locator_engine import LocatorEngine
from app.core.logger import get_logger


class ActionExecutor:
    """Run a single interpreted step and capture evidence on failure."""

    def __init__(self, locator_engine: LocatorEngine | None = None) -> None:
        self.logger = get_logger(__name__)
        self.locator_engine = locator_engine or LocatorEngine()

    async def execute_step(
        self,
        page: Page,
        step_record: InterpretedStepRecord,
        test_data: dict[str, str],
        run_id: str,
        test_case_id: str,
        screenshots_dir: Path,
        html_dir: Path,
        timeout_ms: int | None = None,
    ) -> StepExecutionResult:
        start = time.perf_counter()
        timeout = timeout_ms if timeout_ms is not None else settings.default_timeout_ms
        interpreted = step_record.interpreted

        if interpreted is None:
            return StepExecutionResult(
                step_index=step_record.step_index,
                raw_step=step_record.raw_step,
                status="failed",
                error_type="INTERPRETATION_ERROR",
                error_message=(step_record.interpretation_error or {}).get("error_message"),
                duration_ms=0,
                url=page.url if page else None,
            )

        try:
            action = interpreted.action
            target = interpreted.target
            self.logger.info(
                "run_id=%s testcase=%s step=%s action=%s target=%s status=start",
                run_id,
                test_case_id,
                step_record.step_index,
                action,
                target,
            )
            if action == "goto":
                url = self._resolve_url(target)
                await page.goto(url, timeout=timeout)
                locator_strategy = "navigation"
            elif action == "click":
                locator, locator_strategy = await self.locator_engine.resolve(page, action, target)
                await locator.first.click(timeout=timeout)
            elif action == "fill":
                value = self._resolve_fill_value(interpreted.value, interpreted.value_key, test_data)
                locator, locator_strategy = await self.locator_engine.resolve(page, action, target)
                await locator.first.fill(value, timeout=timeout)
            elif action == "assert_visible":
                assertion_text = (
                    interpreted.assertion.get("text")
                    if interpreted.assertion and interpreted.assertion.get("text")
                    else None
                )
                if assertion_text:
                    await expect(page.get_by_text(assertion_text, exact=False).first).to_be_visible(
                        timeout=timeout
                    )
                    locator_strategy = "text_assert"
                else:
                    locator, locator_strategy = await self.locator_engine.resolve(
                        page, action, target
                    )
                    await expect(locator.first).to_be_visible(timeout=timeout)
            elif action == "assert_text":
                text = interpreted.assertion.get("text") if interpreted.assertion else target
                await expect(page.get_by_text(text, exact=False).first).to_be_visible(
                    timeout=timeout
                )
                locator_strategy = "text_assert"
            elif action == "wait":
                wait_ms = self._safe_wait_ms(interpreted.value)
                await page.wait_for_timeout(wait_ms)
                locator_strategy = "wait"
            else:
                raise ValueError(f"Unsupported action for v1 executor: {action}")

            step_screenshot_path = await self._capture_step_screenshot(
                page=page,
                run_id=run_id,
                test_case_id=test_case_id,
                step_index=step_record.step_index,
                screenshots_dir=screenshots_dir,
            )
            return StepExecutionResult(
                step_index=step_record.step_index,
                raw_step=step_record.raw_step,
                action=interpreted.action,
                target=interpreted.target,
                status="passed",
                locator_strategy=locator_strategy,
                duration_ms=int((time.perf_counter() - start) * 1000),
                url=page.url,
                screenshot_path=step_screenshot_path,
            )
        except (PlaywrightError, ValueError, AssertionError) as exc:
            self.logger.error(
                "run_id=%s testcase=%s step=%s action=%s status=failed error=%s",
                run_id,
                test_case_id,
                step_record.step_index,
                interpreted.action,
                exc,
            )
            screenshot_path, html_path = await self._capture_failure_evidence(
                page,
                run_id=run_id,
                test_case_id=test_case_id,
                step_index=step_record.step_index,
                screenshots_dir=screenshots_dir,
                html_dir=html_dir,
            )
            return StepExecutionResult(
                step_index=step_record.step_index,
                raw_step=step_record.raw_step,
                action=interpreted.action,
                target=interpreted.target,
                status="failed",
                error_type="EXECUTION_ERROR",
                error_message=str(exc),
                duration_ms=int((time.perf_counter() - start) * 1000),
                url=page.url if page else None,
                screenshot_path=screenshot_path,
                html_snapshot_path=html_path,
            )

    @staticmethod
    def _resolve_fill_value(
        explicit_value: str | None,
        value_key: str | None,
        test_data: dict[str, str],
    ) -> str:
        if explicit_value:
            return explicit_value
        if value_key and value_key in test_data:
            return test_data[value_key]
        raise ValueError(f"Missing value for fill action. value_key={value_key!r}")

    @staticmethod
    def _safe_wait_ms(value: str | None) -> int:
        if value is None:
            return 1000
        try:
            return max(200, int(value))
        except ValueError:
            return 1000

    @staticmethod
    def _resolve_url(target: str) -> str:
        t = (target or "").strip().lower()
        if t.startswith("http://") or t.startswith("https://"):
            return target
        if t in {"home page", "website", "home"}:
            return settings.beta_base_url
        return f"{settings.beta_base_url.rstrip('/')}/{target.lstrip('/')}"

    async def _capture_failure_evidence(
        self,
        page: Page,
        run_id: str,
        test_case_id: str,
        step_index: int,
        screenshots_dir: Path,
        html_dir: Path,
    ) -> tuple[str | None, str | None]:
        screenshot_path: str | None = None
        html_path: str | None = None
        stem = f"{run_id}_{test_case_id}_step_{step_index}"

        if settings.screenshot_on_failure:
            screenshot_file = screenshots_dir / f"{stem}.png"
            await page.screenshot(path=str(screenshot_file), full_page=True)
            screenshot_path = str(screenshot_file)

        html_file = html_dir / f"{stem}.html"
        html_file.write_text(await page.content(), encoding="utf-8")
        html_path = str(html_file)
        return screenshot_path, html_path

    async def _capture_step_screenshot(
        self,
        page: Page,
        run_id: str,
        test_case_id: str,
        step_index: int,
        screenshots_dir: Path,
    ) -> str | None:
        screenshot_file = screenshots_dir / f"{run_id}_{test_case_id}_step_{step_index}.png"
        await page.screenshot(path=str(screenshot_file), full_page=True)
        return str(screenshot_file)

