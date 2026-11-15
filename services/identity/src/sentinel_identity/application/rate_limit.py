"""Bounded in-memory login failure limiter (per client IP and per email)."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta

from .ports import Clock

LOGIN_WINDOW = timedelta(minutes=15)
MAX_FAILURES_PER_EMAIL = 5
MAX_FAILURES_PER_IP = 20
MAX_TRACKED_KEYS = 10_000


class LoginRateLimiter:
    """Sliding-window count of failed logins (unknown email or wrong password).

    shortcut: per-process memory, not shared across identity replicas; move to
    Postgres/Redis before running more than one identity process.
    """

    def __init__(
        self,
        clock: Clock,
        *,
        window: timedelta = LOGIN_WINDOW,
        max_per_email: int = MAX_FAILURES_PER_EMAIL,
        max_per_ip: int = MAX_FAILURES_PER_IP,
        max_keys: int = MAX_TRACKED_KEYS,
    ) -> None:
        self._clock = clock
        self._window = window
        self._limits = {"email": max_per_email, "ip": max_per_ip}
        self._max_keys = max_keys
        self._hits: dict[tuple[str, str], deque[datetime]] = {}

    def is_limited(self, *, email: str, ip: str) -> bool:
        return any(self._count(key) >= self._limits[key[0]] for key in _keys(email, ip))

    def record_failure(self, *, email: str, ip: str) -> None:
        now = self._clock.now()
        for key in _keys(email, ip):
            self._count(key)  # prune expired hits first
            self._hits.setdefault(key, deque()).append(now)
        while len(self._hits) > self._max_keys:
            # Evict the oldest-inserted key: bounded memory beats perfect recall.
            self._hits.pop(next(iter(self._hits)))

    def reset_email(self, email: str) -> None:
        self._hits.pop(("email", email), None)

    def _count(self, key: tuple[str, str]) -> int:
        hits = self._hits.get(key)
        if hits is None:
            return 0
        cutoff = self._clock.now() - self._window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if not hits:
            del self._hits[key]
            return 0
        return len(hits)


def _keys(email: str, ip: str) -> list[tuple[str, str]]:
    return [("email", email), ("ip", ip)] if ip else [("email", email)]
