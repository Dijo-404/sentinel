"""Narrow ports the use cases depend on. Adapters raise UpstreamUnavailableError on failure."""

from __future__ import annotations

from typing import Any, Protocol


class ChatModel(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str:
        """Return the assistant message content (may be empty or non-JSON)."""
        ...


class KnowledgeSearch(Protocol):
    def search(self, query: str) -> list[dict[str, Any]]:
        """Return knowledge hits as {article_id, title, summary}."""
        ...
