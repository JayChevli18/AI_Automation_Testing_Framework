"""Excel parsing with flexible column mapping and step splitting."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from app.models.testcase_models import RawExcelRow


class ExcelParser:
    """Parse Excel files into canonical raw testcase rows."""

    _COLUMN_ALIASES: dict[str, set[str]] = {
        "module": {"module", "feature", "component"},
        "test_case_id": {"test case id", "tc id", "id", "testcase id"},
        "test_case_name": {"test case name", "testcase name", "title", "name"},
        "scenario": {"scenario", "description"},
        "preconditions": {"preconditions", "precondition", "given"},
        "test_steps": {"test steps", "steps", "teststep", "step"},
        "test_data": {"test data", "data", "input data"},
        "expected_result": {
            "expected result",
            "expected",
            "result",
            "expected outcome",
        },
    }

    def parse_excel(self, file_path: Path) -> list[RawExcelRow]:
        """Parse Excel and map recognized columns to canonical fields."""
        dataframe = pd.read_excel(file_path)
        if dataframe.empty:
            return []

        column_map = self.detect_columns([str(col) for col in dataframe.columns])
        rows: list[RawExcelRow] = []

        for _, row in dataframe.iterrows():
            mapped = {
                canonical: self._safe_str(row.get(original_col, ""))
                for canonical, original_col in column_map.items()
            }
            raw = RawExcelRow(
                module=mapped.get("module", ""),
                test_case_id=mapped.get("test_case_id", ""),
                test_case_name=mapped.get("test_case_name", ""),
                scenario=mapped.get("scenario", ""),
                preconditions=mapped.get("preconditions", ""),
                test_steps=mapped.get("test_steps", ""),
                test_data=mapped.get("test_data", ""),
                expected_result=mapped.get("expected_result", ""),
            )
            rows.append(raw)

        return rows

    def detect_columns(self, columns: list[str]) -> dict[str, str]:
        """Detect canonical column mapping from flexible input headers."""
        normalized_to_original = {self._norm(col): col for col in columns}
        mapping: dict[str, str] = {}

        for canonical, aliases in self._COLUMN_ALIASES.items():
            for alias in aliases:
                key = self._norm(alias)
                if key in normalized_to_original:
                    mapping[canonical] = normalized_to_original[key]
                    break

        return mapping

    def split_steps(self, raw_steps: str) -> list[str]:
        """Split multiline/manual test steps into action lines."""
        if not raw_steps:
            return []

        steps = raw_steps.replace("\r\n", "\n").replace("\r", "\n").strip()
        # Handle inline numbering in a single line, e.g. "Open ... 2. Click ... 3. Enter ...".
        steps = re.sub(r"\s+(?=\d+[\.\)]\s+)", "\n", steps)
        # Handle inline bullets.
        steps = re.sub(r"\s+(?=[-*]\s+)", "\n", steps)

        # Split by newline first.
        parts = [part.strip() for part in steps.split("\n") if part.strip()]
        if len(parts) <= 1:
            # Fall back to semicolon-delimited if newline split still yields one block.
            parts = [part.strip() for part in steps.split(";") if part.strip()]

        cleaned: list[str] = []
        for part in parts:
            # Remove numbering/bullets like "1.", "2)", "-", "*".
            normalized = re.sub(r"^\s*(\d+[\.\)]|[-*])\s*", "", part).strip()
            if normalized:
                cleaned.append(normalized)
        return cleaned

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower())

    @staticmethod
    def _safe_str(value: object) -> str:
        if value is None:
            return ""
        # pandas may produce NaN for empty cells.
        if isinstance(value, float) and pd.isna(value):
            return ""
        return str(value).strip()

