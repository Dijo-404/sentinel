"""Injectable clocks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _iso(instant: datetime) -> str:
    return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class SystemClock:
    def now_iso(self) -> str:
        return _iso(datetime.now(UTC))


class FixedClock:
    def __init__(self, instant: datetime):
        self._instant = instant

    def now_iso(self) -> str:
        return _iso(self._instant)

    def advance(self, **kwargs) -> None:
        self._instant = self._instant + timedelta(**kwargs)
