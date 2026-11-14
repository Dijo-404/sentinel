"""Detect accidental network use inside the reservation transaction.

State lives in contextvars so a process-wide guard instance stays request-safe
under FastAPI/anyio threadpool concurrency.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from sentinel_action_ledger.domain.errors import ConflictError

_active: ContextVar[bool] = ContextVar("reservation_network_active", default=False)
_calls: ContextVar[int] = ContextVar("reservation_network_calls", default=0)


class ReservationNetworkGuard:
    @contextmanager
    def begin_guard(self) -> Iterator[None]:
        token_active = _active.set(True)
        token_calls = _calls.set(0)
        try:
            yield
        finally:
            _active.reset(token_active)
            _calls.reset(token_calls)

    def assert_idle(self) -> None:
        if _calls.get():
            raise ConflictError(
                "Network call occurred inside reservation transaction",
                code="NETWORK_IN_TX",
            )

    def note_network(self) -> None:
        if _active.get():
            _calls.set(_calls.get() + 1)
