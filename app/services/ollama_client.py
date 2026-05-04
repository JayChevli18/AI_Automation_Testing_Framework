"""HTTP client for local Ollama LLM."""

from __future__ import annotations

import logging
from typing import Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Calls Ollama /api/generate for non-streaming completions."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.model = model or settings.ollama_model

    def generate_text(
        self,
        prompt: str,
        timeout_s: int | None = None,
        system_prefix: str | None = None,
        json_format: bool = True,
    ) -> str:
        """Return raw model response string."""
        return self._generate_raw(
            prompt=prompt,
            timeout_s=timeout_s,
            system_prefix=system_prefix,
            json_format=json_format,
        )

    def generate_json(
        self,
        prompt: str,
        timeout_s: int | None = None,
        system_prefix: str | None = None,
    ) -> dict[str, Any]:
        """Return parsed JSON object from model response text."""
        text = self.generate_text(
            prompt=prompt,
            timeout_s=timeout_s,
            system_prefix=system_prefix,
            json_format=True,
        )
        from app.utils.json_utils import extract_json_object

        data = extract_json_object(text)
        if data is None:
            raise ValueError(f"Ollama returned non-JSON output: {text[:500]!r}")
        return data

    def _generate_raw(
        self,
        prompt: str,
        timeout_s: int | None = None,
        system_prefix: str | None = None,
        json_format: bool = False,
    ) -> str:
        timeout = timeout_s if timeout_s is not None else settings.ollama_timeout_s
        full_prompt = f"{system_prefix}\n\n{prompt}" if system_prefix else prompt
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
        if json_format and settings.ollama_json_format:
            payload["format"] = "json"

        url = f"{self.base_url}/api/generate"
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Ollama request failed: %s", exc)
            raise ConnectionError(f"Ollama request failed: {exc}") from exc

        body = response.json()
        return str(body.get("response", ""))

    def healthcheck(self) -> bool:
        """Return True if Ollama responds on /api/tags."""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.ok
        except requests.RequestException:
            return False
