"""Models for raw and normalized test case data."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RawExcelRow(BaseModel):
    """Raw parsed row mapped to canonical fields before normalization."""

    module: str = ""
    test_case_id: str = ""
    test_case_name: str = ""
    scenario: str = ""
    preconditions: str = ""
    test_steps: str = ""
    test_data: str = ""
    expected_result: str = ""


class NormalizedTestCase(BaseModel):
    """Normalized testcase structure used by downstream services."""

    module: str = ""
    test_case_id: str = ""
    test_case_name: str = ""
    scenario: str = ""
    preconditions: str = ""
    steps: list[str] = Field(default_factory=list)
    test_data: dict[str, str] = Field(default_factory=dict)
    expected_result: str = ""

