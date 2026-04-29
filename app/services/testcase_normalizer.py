"""Normalize raw testcase rows into standard JSON-ready shape."""

from __future__ import annotations

import re

from app.models.testcase_models import NormalizedTestCase, RawExcelRow
from app.services.excel_parser import ExcelParser


class TestcaseNormalizer:
    """Converts raw rows into normalized testcase objects."""

    def __init__(self, parser: ExcelParser | None = None) -> None:
        self.parser = parser or ExcelParser()

    def normalize(self, raw_rows: list[RawExcelRow]) -> list[NormalizedTestCase]:
        """Clean rows, split steps, and parse structured test data."""
        normalized_cases: list[NormalizedTestCase] = []

        for row in raw_rows:
            if not self._has_core_content(row):
                continue

            normalized = NormalizedTestCase(
                module=self._clean(row.module),
                test_case_id=self._clean(row.test_case_id),
                test_case_name=self._clean(row.test_case_name),
                scenario=self._clean(row.scenario),
                preconditions=self._clean(row.preconditions),
                steps=self.parser.split_steps(self._clean(row.test_steps)),
                test_data=self.parse_test_data(self._clean(row.test_data)),
                expected_result=self._clean(row.expected_result),
            )
            normalized_cases.append(normalized)

        return normalized_cases

    def parse_test_data(self, raw_test_data: str | None) -> dict[str, str]:
        """Parse 'key: value; key2: value2' style data to dict."""
        if not raw_test_data:
            return {}

        pairs = re.split(r"[;\n]", raw_test_data)
        parsed: dict[str, str] = {}
        for pair in pairs:
            token = pair.strip()
            if not token:
                continue
            if ":" in token:
                key, value = token.split(":", 1)
            elif "=" in token:
                key, value = token.split("=", 1)
            else:
                continue
            k = self._clean(key).lower().replace(" ", "_")
            v = self._clean(value)
            if k:
                parsed[k] = v
        return parsed

    def validate_required_fields(self, case: NormalizedTestCase) -> list[str]:
        """Return missing required field names for a normalized test case."""
        missing: list[str] = []
        if not case.test_case_id:
            missing.append("test_case_id")
        if not case.test_case_name:
            missing.append("test_case_name")
        if not case.steps:
            missing.append("steps")
        return missing

    @staticmethod
    def _has_core_content(row: RawExcelRow) -> bool:
        return any(
            [
                row.module,
                row.test_case_id,
                row.test_case_name,
                row.test_steps,
                row.expected_result,
            ]
        )

    @staticmethod
    def _clean(value: str) -> str:
        cleaned = value.replace("_x000d_", " ").replace("\\n", " ")
        return re.sub(r"\s+", " ", cleaned).strip()

