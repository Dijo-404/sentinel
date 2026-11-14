"""Framework-free wire-aligned types for knowledge.v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CONTRACT_VERSION = "sentinel.task-contracts.v1"

ALLOWED_ROLES = frozenset({"operator", "supervisor"})


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
