"""Sarvam AI chat-completions adapter (OpenAI-style body, `api-subscription-key` header)."""

from __future__ import annotations

import httpx

from ..application.errors import ConfigurationError, UpstreamUnavailableError


class SarvamChat:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = "https://api.sarvam.ai",
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout_s: float = 9.0,
        reasoning_effort: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ConfigurationError("SARVAM_API_KEY is required")
        self._key = api_key
        self.model = model
        self._url = f"{base_url.rstrip('/')}/v1/chat/completions"
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout_s = timeout_s
        self._reasoning_effort = reasoning_effort
        self._client = client or httpx.Client()

    def complete(self, messages: list[dict[str, str]]) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            # Reasoning models spend completion tokens thinking before the answer.
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            # null disables reasoning: with it on, sarvam-105b took 15-54s per call live,
            # past the workflow/assistant callers' fixed 10s timeouts.
            "reasoning_effort": self._reasoning_effort,
        }
        try:
            response = self._client.post(
                self._url,
                json=body,
                headers={"api-subscription-key": self._key},
                timeout=self._timeout_s,
            )
        except httpx.HTTPError as exc:
            raise UpstreamUnavailableError(f"sarvam unreachable: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise UpstreamUnavailableError(f"sarvam returned {response.status_code}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise UpstreamUnavailableError("sarvam returned a malformed envelope") from exc
        return content if isinstance(content, str) else ""
