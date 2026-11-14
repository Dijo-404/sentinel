"""Ports for signal persistence."""

from __future__ import annotations

from typing import Protocol

from ..domain.types import Signal


class SignalStore(Protocol):
    def put(self, item: Signal) -> None: ...

    def list_signals(self, tenant_id: str, *, limit: int) -> list[Signal]: ...
