"""In-memory signal store for fixture tests."""

from __future__ import annotations

from ..domain.types import Signal


class MemorySignalStore:
    def __init__(self) -> None:
        self._items: dict[str, Signal] = {}

    def put(self, item: Signal) -> None:
        self._items[item.signal_id] = item

    def list_signals(self, tenant_id: str, *, limit: int) -> list[Signal]:
        rows = [item for item in self._items.values() if item.tenant_id == tenant_id]
        rows.sort(key=lambda item: item.recorded_at, reverse=True)
        return rows[:limit]
