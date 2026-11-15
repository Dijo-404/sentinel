"""knowledge.v1 `GET /v1/search?q=` client (bearer token with operator/supervisor role)."""

from __future__ import annotations

from typing import Any

import httpx

from ..application.errors import ConfigurationError, UpstreamUnavailableError


class HttpKnowledgeSearch:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        limit: int = 5,
        timeout_s: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not base_url or not token:
            raise ConfigurationError(
                "MODEL_GATEWAY_KNOWLEDGE_URL and MODEL_GATEWAY_KNOWLEDGE_TOKEN are required"
            )
        self._url = f"{base_url.rstrip('/')}/v1/search"
        self._token = token
        self._limit = limit
        self._timeout_s = timeout_s
        self._client = client or httpx.Client()

    def search(self, query: str) -> list[dict[str, Any]]:
        try:
            response = self._client.get(
                self._url,
                params={"q": query},
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=self._timeout_s,
            )
        except httpx.HTTPError as exc:
            raise UpstreamUnavailableError(f"knowledge unreachable: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise UpstreamUnavailableError(f"knowledge returned {response.status_code}")
        try:
            hits = response.json()["hits"]
            return [
                {"article_id": h["article_id"], "title": h["title"], "summary": h["summary"]}
                for h in hits[: self._limit]
            ]
        except (ValueError, KeyError, TypeError) as exc:
            raise UpstreamUnavailableError("knowledge returned a malformed body") from exc
