"""Wire and domain types for ops-activity.v1."""

from __future__ import annotations

from dataclasses import dataclass

CONTRACT_VERSION = "sentinel.task-contracts.v1"
FEED_LIMIT = 50
ALLOWED_ROLES = frozenset({"operator", "supervisor"})


@dataclass(frozen=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]


@dataclass(frozen=True)
class ActivityItem:
    activity_id: str
    tenant_id: str
    kind: str
    summary: str
    occurred_at: str
    case_id: str | None = None

    def to_wire(self) -> dict:
        payload = {
            "activity_id": self.activity_id,
            "kind": self.kind,
            "summary": self.summary,
            "occurred_at": self.occurred_at,
        }
        if self.case_id is not None:
            payload["case_id"] = self.case_id
        return payload
