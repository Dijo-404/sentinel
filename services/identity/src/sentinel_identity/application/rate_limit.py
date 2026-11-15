"""Bounded, thread-safe login failure limits per account/client and client IP."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from threading import Lock

from .ports import Clock

LOGIN_WINDOW = timedelta(minutes=15)
MAX_FAILURES_PER_EMAIL = 5
MAX_FAILURES_PER_IP = 20
MAX_TRACKED_KEYS = 10_000


class LoginRateLimiter:
    """Sliding-window failures; capacity exhaustion never evicts active limits.

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
        self._hits: dict[tuple[str, ...], deque[datetime]] = {}
        self._lock = Lock()

    def is_limited(self, *, email: str, ip: str) -> bool:
        with self._lock:
            self._prune(self._clock.now())
            return self._limited(_keys(email, ip))

    def record_failure(self, *, email: str, ip: str) -> bool:
        """Atomically admit one failure, or deny without changing active buckets."""
        with self._lock:
            now = self._clock.now()
            self._prune(now)
            keys = _keys(email, ip)
            if self._limited(keys):
                return False
            for key in keys:
                self._hits.setdefault(key, deque()).append(now)
            return True

    def reset_email(self, email: str, *, ip: str = "") -> None:
        # A successful login cannot erase another client's failures or the IP limit.
        with self._lock:
            self._hits.pop(("email", email, ip), None)

    def _limited(self, keys: list[tuple[str, ...]]) -> bool:
        missing = sum(key not in self._hits for key in keys)
        return len(self._hits) + missing > self._max_keys or any(
            len(self._hits.get(key, ())) >= self._limits[key[0]] for key in keys
        )

    def _prune(self, now: datetime) -> None:
        cutoff = now - self._window
        for key, hits in list(self._hits.items()):
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if not hits:
                del self._hits[key]


def _keys(email: str, ip: str) -> list[tuple[str, ...]]:
    return [("email", email, ip), ("ip", ip)] if ip else [("email", email, "")]
