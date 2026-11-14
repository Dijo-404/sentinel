"""Ports for activity persistence."""

from __future__ import annotations

from typing import Protocol

from ..domain.types import ActivityItem


class ActivityStore(Protocol):
    def put(self, item: ActivityItem) -> None: ...

    def list_activity(self, tenant_id: str, *, limit: int) -> list[ActivityItem]: ...
