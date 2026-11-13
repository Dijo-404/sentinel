"""In-memory draft store for standalone checks and local preview."""

from __future__ import annotations

import itertools
from datetime import UTC, datetime

from sentinel_merchant_comms.domain.types import CommsDraft


class InMemoryDraftStore:
    def __init__(self) -> None:
        self._items: dict[str, CommsDraft] = {}

    def save(self, draft: CommsDraft) -> CommsDraft:
        self._items[draft.draft_id] = draft
        return draft

    def get(self, draft_id: str) -> CommsDraft | None:
        return self._items.get(draft_id)


class FixedClock:
    def __init__(self, now: str = "2026-11-13T19:30:00Z") -> None:
        self._now = now

    def now_rfc3339(self) -> str:
        return self._now


class SystemClock:
    def now_rfc3339(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class SequentialIds:
    def __init__(self, prefix: str = "draft-demo") -> None:
        self._counter = itertools.count(1)
        self._prefix = prefix

    def new_draft_id(self) -> str:
        return f"{self._prefix}-{next(self._counter)}"
