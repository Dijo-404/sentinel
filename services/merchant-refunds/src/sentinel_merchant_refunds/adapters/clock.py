"""UTC clock adapter."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    def now_iso(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class FixedClock:
    def __init__(self, value: str = "2026-11-13T12:00:00Z") -> None:
        self.value = value

    def now_iso(self) -> str:
        return self.value
