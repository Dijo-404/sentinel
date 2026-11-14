"""Identifier generators."""

from __future__ import annotations

import secrets
import threading


class SecureIdGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{secrets.token_hex(8)}"


class SequenceIdGenerator:
    def __init__(self) -> None:
        self._n = 0
        self._lock = threading.Lock()

    def new_id(self, prefix: str) -> str:
        with self._lock:
            self._n += 1
            return f"{prefix}-{self._n:04d}"
