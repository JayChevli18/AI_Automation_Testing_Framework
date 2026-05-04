"""Per-testcase cache of successful locator recipes for faster re-resolution."""

from __future__ import annotations

from typing import Any


class SelectorCache:
    """Maps a stable step key to the last successful locator recipe (JSON-serializable dict)."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> dict[str, Any] | None:
        return self._data.get(key)

    def set(self, key: str, recipe: dict[str, Any]) -> None:
        self._data[key] = recipe

    def clear_key(self, key: str) -> None:
        self._data.pop(key, None)
