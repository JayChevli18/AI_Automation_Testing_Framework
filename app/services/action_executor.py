"""Execute interpreted actions against a Playwright page."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page, expect

from app.config import settings
from app.models.execution_models import StepExecutionResult
from app.models.interpreted_models import InterpretedStepRecord
from app.services.locator_engine import LocatorEngine
from app.services.selector_cache import SelectorCache
from app.core.logger import get_logger


class ActionExecutor:
    """Run a single interpreted step and capture evidence on failure."""

    def __init__(self, locator_engine: LocatorEngine | None = None) -> None:
        self.logger = get_logger(__name__)
        self.locator_engine = locator_engine or LocatorEngine()

    def _locator_cache_key(
        self, test_case_id: str, step_index: int, action: str, target: str
    ) -> str:
        return f"{test_case_id}:{step_index}:{action}:{target}"

    def _live_mutation_blocked(self, environment: str, allow_live_mutations: bool, action: str) -> bool:
        return (
            environment == "live"
            and not allow_live_mutations
            and action in ("click", "fill", "hover")
        )

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
        *,
        environment: str = "beta",
        allow_live_mutations: bool = False,
        base_url: str | None = None,
        selector_cache: SelectorCache | None = None,
    ) -> StepExecutionResult:
        start = time.perf_counter()
        timeout = timeout_ms if timeout_ms is not None else settings.default_timeout_ms
        root_url = (base_url or settings.beta_base_url).rstrip("/")
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
                attempts=1,
            )

        action = interpreted.action
        target = interpreted.target or ""

        if self._live_mutation_blocked(environment, allow_live_mutations, action):
            return StepExecutionResult(
                step_index=step_record.step_index,
                raw_step=step_record.raw_step,
                action=action,
                target=target,
                status="failed",
                error_type="LIVE_SAFE_MODE",
                error_message=(
                    "Mutating actions (click/fill/hover) are blocked on environment=live "
                    "unless allow_live_mutations=true on the run request."
                ),
                duration_ms=int((time.perf_counter() - start) * 1000),
                url=page.url if page else None,
                attempts=0,
            )

        cache_key = self._locator_cache_key(test_case_id, step_record.step_index, action, target)

        try:
            self.logger.info(
                "run_id=%s testcase=%s step=%s action=%s target=%s status=start",
                run_id,
                test_case_id,
                step_record.step_index,
                action,
                target,
            )
            locator_strategy = ""
            attempts_used = 0

            if action == "goto":
                url = self._resolve_url(target, root_url)
                await page.goto(url, timeout=timeout)
                locator_strategy = "navigation"
                attempts_used = 1
            elif action == "hover":
                locator_strategy, attempts_used = await self._retry_interaction(
                    page=page,
                    action=action,
                    target=target,
                    timeout=timeout,
                    selector_cache=selector_cache,
                    cache_key=cache_key,
                    runner=lambda loc: loc.first.hover(timeout=timeout),
                )
            elif action == "click":
                locator_strategy, attempts_used = await self._retry_interaction(
                    page=page,
                    action=action,
                    target=target,
                    timeout=timeout,
                    selector_cache=selector_cache,
                    cache_key=cache_key,
                    runner=lambda loc: loc.first.click(timeout=timeout),
                )
            elif action == "fill":
                value = self._resolve_fill_value(interpreted.value, interpreted.value_key, test_data)
                locator_strategy, attempts_used = await self._retry_interaction(
                    page=page,
                    action=action,
                    target=target,
                    timeout=timeout,
                    selector_cache=selector_cache,
                    cache_key=cache_key,
                    runner=lambda loc: loc.first.fill(value, timeout=timeout),
                )
            elif action == "assert_visible":
                assertion_text = (
                    interpreted.assertion.get("text")
                    if interpreted.assertion and interpreted.assertion.get("text")
                    else None
                )
                if assertion_text:
                    attempts_used = await self._retry_assert(
                        lambda: self._assert_any_visible_text(page, assertion_text, timeout),
                    )
                    locator_strategy = "text_assert"
                else:
                    locator_strategy, attempts_used = await self._retry_interaction(
                        page=page,
                        action=action,
                        target=target,
                        timeout=timeout,
                        selector_cache=selector_cache,
                        cache_key=cache_key,
                        runner=lambda loc: expect(loc.first).to_be_visible(timeout=timeout),
                    )
            elif action == "assert_text":
                text = interpreted.assertion.get("text") if interpreted.assertion else target
                attempts_used = await self._retry_assert(
                    lambda: self._assert_any_visible_text(page, text, timeout),
                )
                locator_strategy = "text_assert"
            elif action == "wait":
                wait_ms = self._safe_wait_ms(interpreted.value)
                await page.wait_for_timeout(wait_ms)
                locator_strategy = "wait"
                attempts_used = 1
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
                attempts=attempts_used,
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
            pw_name = getattr(exc, "name", None) or type(exc).__name__
            detail = str(exc).strip() or repr(exc)
            return StepExecutionResult(
                step_index=step_record.step_index,
                raw_step=step_record.raw_step,
                action=interpreted.action,
                target=interpreted.target,
                status="failed",
                error_type="EXECUTION_ERROR",
                error_message=f"[{pw_name}] {detail}",
                duration_ms=int((time.perf_counter() - start) * 1000),
                url=page.url if page else None,
                attempts=settings.step_retry_max,
                screenshot_path=screenshot_path,
                html_snapshot_path=html_path,
            )

    async def _retry_assert(self, op: Callable[[], Awaitable[None]]) -> int:
        last: BaseException | None = None
        for attempt in range(1, settings.step_retry_max + 1):
            try:
                await op()
                return attempt
            except (PlaywrightError, AssertionError) as exc:
                last = exc
                if attempt < settings.step_retry_max:
                    await asyncio.sleep(settings.step_retry_delay_ms / 1000)
        assert last is not None
        raise last

    @staticmethod
    async def _assert_any_visible_text(page: Page, text: str, timeout: int) -> None:
        """Pass when any element containing text is visible.

        get_by_text(...).first can resolve to hidden nodes (e.g., hidden <option>).
        We scan all matches and succeed if at least one is visible.
        """
        needle = (text or "").strip()
        if not needle:
            raise AssertionError("Expected assertion text is empty.")

        locator = page.get_by_text(needle, exact=False)
        await expect(locator.first).to_be_attached(timeout=timeout)

        count = await locator.count()
        for i in range(count):
            if await locator.nth(i).is_visible():
                return
        raise AssertionError(f"Text '{needle}' was found but no visible match was detected.")

    async def _retry_interaction(
        self,
        page: Page,
        action: str,
        target: str,
        timeout: int,
        selector_cache: SelectorCache | None,
        cache_key: str,
        runner: Callable[[Locator], Awaitable[None]],
    ) -> tuple[str, int]:
        last: BaseException | None = None
        locator_strategy = ""
        for attempt in range(1, settings.step_retry_max + 1):
            try:
                if attempt > 1 and selector_cache is not None:
                    selector_cache.clear_key(cache_key)
                locator, locator_strategy, recipe = await self.locator_engine.resolve(
                    page,
                    action,
                    target,
                    cache=selector_cache if attempt == 1 else None,
                    cache_key=cache_key if attempt == 1 else None,
                )
                if attempt > 1:
                    await locator.first.scroll_into_view_if_needed(timeout=timeout)
                await runner(locator)
                if recipe is not None and selector_cache is not None:
                    selector_cache.set(cache_key, recipe)
                return locator_strategy, attempt
            except (PlaywrightError, ValueError) as exc:
                last = exc
                if attempt < settings.step_retry_max:
                    await asyncio.sleep(settings.step_retry_delay_ms / 1000)
        assert last is not None
        raise last

    @staticmethod
    def _resolve_fill_value(
        explicit_value: str | None,
        value_key: str | None,
        test_data: dict[str, str],
    ) -> str:
        """Resolve text to type into a field.

        Prefer ``test_data[value_key]`` whenever that key exists. The LLM often
        wrongly sets ``value`` to the placeholder word ``password`` / ``email``;
        those must not override real credentials from the sheet.
        """
        explicit = (explicit_value or "").strip() if explicit_value is not None else ""
        if value_key and value_key in test_data:
            return test_data[value_key]
        if explicit:
            return explicit
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
    def _resolve_url(target: str, base_url: str) -> str:
        t = (target or "").strip().lower()
        raw = (target or "").strip()
        if t.startswith("http://") or t.startswith("https://"):
            return raw
        root = base_url.rstrip("/")
        if t in {"home page", "website", "home"}:
            return f"{root}/"
        return f"{root}/{raw.lstrip('/')}"

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
