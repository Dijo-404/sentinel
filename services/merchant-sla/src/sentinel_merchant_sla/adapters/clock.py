"""System, fixed, and virtual clocks for SLA evaluation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        self._instant = instant.astimezone(UTC)

    def now(self) -> datetime:
        return self._instant

    def set(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        self._instant = instant.astimezone(UTC)

    def advance(self, *, seconds: int) -> datetime:
        self._instant = self._instant + timedelta(seconds=seconds)
        return self._instant
