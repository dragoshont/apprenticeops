"""Thin async client for a local Ollama server.

This is a real network client. There is no mock path: `version`, `tags`, and
`generate` all issue HTTP requests to the configured Ollama endpoint and raise
`OllamaError` on any failure so the API layer can translate it into an honest
error response rather than pretending an inference happened.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class OllamaError(RuntimeError):
    """Raised when the Ollama backend is unreachable or returns an error."""


@dataclass
class InferenceResult:
    model: str
    response: str
    total_duration_ns: int | None
    eval_count: int | None
    prompt_eval_count: int | None
    created_at: str | None
    done_reason: str | None

    @property
    def total_duration_ms(self) -> float | None:
        if self.total_duration_ns is None:
            return None
        return round(self.total_duration_ns / 1e6, 1)

    @property
    def tokens_per_second(self) -> float | None:
        if not self.eval_count or not self.total_duration_ns:
            return None
        seconds = self.total_duration_ns / 1e9
        if seconds <= 0:
            return None
        return round(self.eval_count / seconds, 2)


class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 300.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def version(self) -> str:
        data = await self._get_json("/api/version")
        return str(data.get("version", "unknown"))

    async def tags(self) -> list[dict[str, Any]]:
        data = await self._get_json("/api/tags")
        models = data.get("models", [])
        if not isinstance(models, list):
            raise OllamaError("unexpected /api/tags payload from Ollama")
        return models

    async def model_names(self) -> list[str]:
        return [str(m.get("name")) for m in await self.tags() if m.get("name")]

    async def generate(
        self,
        model: str,
        prompt: str,
        options: dict[str, Any] | None = None,
    ) -> InferenceResult:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if options:
            payload["options"] = options
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(f"{self._base_url}/api/generate", json=payload)
        except httpx.HTTPError as exc:  # connection/timeout errors
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        if resp.status_code != 200:
            raise OllamaError(
                f"Ollama returned {resp.status_code}: {resp.text[:400]}"
            )
        data = resp.json()
        if "response" not in data:
            raise OllamaError(f"Ollama response missing 'response': {data}")
        return InferenceResult(
            model=str(data.get("model", model)),
            response=str(data["response"]),
            total_duration_ns=data.get("total_duration"),
            eval_count=data.get("eval_count"),
            prompt_eval_count=data.get("prompt_eval_count"),
            created_at=data.get("created_at"),
            done_reason=data.get("done_reason"),
        )

    async def _get_json(self, path: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=min(self._timeout, 15.0)) as client:
                resp = await client.get(f"{self._base_url}{path}")
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request to {path} failed: {exc}") from exc
        if resp.status_code != 200:
            raise OllamaError(f"Ollama {path} returned {resp.status_code}")
        return resp.json()
