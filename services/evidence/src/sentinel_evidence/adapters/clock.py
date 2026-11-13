"""Injectable clocks."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    def __init__(self, instant: datetime):
        self._instant = instant

    def now(self) -> datetime:
        return self._instant
