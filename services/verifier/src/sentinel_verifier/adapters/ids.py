"""Identifier generators."""

from __future__ import annotations

import secrets


class SecureIdGenerator:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{secrets.token_hex(8)}"


class SequenceIdGenerator:
    def __init__(self) -> None:
        self._n = 0

    def new_id(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}-{self._n:04d}"
