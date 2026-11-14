"""In-memory activity store for fixture tests."""

from __future__ import annotations

from ..domain.types import ActivityItem


class MemoryActivityStore:
    def __init__(self) -> None:
        self._items: dict[str, ActivityItem] = {}

    def put(self, item: ActivityItem) -> None:
        self._items[item.activity_id] = item

    def list_activity(self, tenant_id: str, *, limit: int) -> list[ActivityItem]:
        rows = [item for item in self._items.values() if item.tenant_id == tenant_id]
        rows.sort(key=lambda item: item.occurred_at, reverse=True)
        return rows[:limit]
