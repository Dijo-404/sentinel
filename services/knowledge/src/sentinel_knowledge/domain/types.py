"""Framework-free wire-aligned types for knowledge.v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONTRACT_VERSION = "sentinel.task-contracts.v1"

ALLOWED_ROLES = frozenset({"operator", "supervisor"})

# Hybrid ranking: cosine similarity plus a small bonus when the literal query
# appears in title/summary/body, so exact phrase matches stay near the top.
KEYWORD_BONUS = 0.05
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]

    def allows_knowledge(self) -> bool:
        return bool(ALLOWED_ROLES.intersection(self.roles))


@dataclass(frozen=True, slots=True)
class Article:
    article_id: str
    tenant_id: str
    title: str
    summary: str
    body: str
    updated_at: str

    def to_list_wire(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "title": self.title,
            "summary": self.summary,
            "updated_at": self.updated_at,
        }

    def to_detail_wire(self) -> dict[str, Any]:
        return {
            **self.to_list_wire(),
            "body": self.body,
        }

    def to_hit_wire(self) -> dict[str, Any]:
        return self.to_list_wire()

    def passage_text(self) -> str:
        return f"{self.title}\n{self.summary}\n{self.body}"


@dataclass(frozen=True, slots=True)
class SearchHit:
    article: Article
    score: float | None = None  # None on the fixture substring path

    def to_wire(self) -> dict[str, Any]:
        wire = self.article.to_hit_wire()
        if self.score is not None:
            wire["score"] = round(self.score, 6)
        return wire
