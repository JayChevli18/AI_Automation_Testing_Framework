"""Reusable helpers for list/search/filter/sort/pagination APIs."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any


def _coerce_dt(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


def _matches_filter(
    current: object,
    operator: str,
    value: object,
    *,
    treat_as_datetime: bool,
) -> bool:
    if treat_as_datetime:
        lhs = _coerce_dt(current)
        rhs = _coerce_dt(value)
        if lhs is None or rhs is None:
            return False
        if operator == "equals":
            return lhs == rhs
        if operator == "gte":
            return lhs >= rhs
        if operator == "lte":
            return lhs <= rhs
        if operator == "contains":
            return rhs.isoformat() in lhs.isoformat()
        return False

    lhs_text = str(current).lower()
    rhs_text = str(value).lower()
    if operator == "equals":
        return lhs_text == rhs_text
    if operator == "contains":
        return rhs_text in lhs_text
    if operator == "gte":
        return lhs_text >= rhs_text
    if operator == "lte":
        return lhs_text <= rhs_text
    return False


def apply_listing_query(
    items: Sequence[Any],
    *,
    page: int,
    limit: int,
    search: str | None,
    search_getters: Sequence[Callable[[Any], str]],
    filters: Sequence[Any],
    sort_by: str,
    sort_order: str,
    value_getter: Callable[[Any, str], object],
    datetime_fields: set[str] | None = None,
) -> tuple[list[Any], int]:
    """Apply common list query operations and return (paged_rows, total_before_page)."""
    rows = list(items)
    datetime_fields = datetime_fields or set()

    if search:
        token = search.strip().lower()
        if token:
            rows = [r for r in rows if any(token in getter(r).lower() for getter in search_getters)]

    for f in filters:
        rows = [
            r
            for r in rows
            if _matches_filter(
                value_getter(r, f.field),
                f.operator,
                f.value,
                treat_as_datetime=f.field in datetime_fields,
            )
        ]

    rows.sort(
        key=lambda r: value_getter(r, sort_by),
        reverse=sort_order == "desc",
    )

    total = len(rows)
    start = (page - 1) * limit
    end = start + limit
    return rows[start:end], total
