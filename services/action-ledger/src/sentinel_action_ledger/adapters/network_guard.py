"""Detect accidental network use inside the reservation transaction."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sentinel_action_ledger.domain.errors import ConflictError


class ReservationNetworkGuard:
    def __init__(self) -> None:
        self._active = False
        self._calls = 0

    @contextmanager
    def begin_guard(self) -> Iterator[None]:
        self._active = True
        self._calls = 0
        try:
            yield
        finally:
            self._active = False

    def assert_idle(self) -> None:
        if self._calls:
            raise ConflictError(
                "Network call occurred inside reservation transaction",
                code="NETWORK_IN_TX",
            )

    def note_network(self) -> None:
        if self._active:
            self._calls += 1
