from __future__ import annotations

from typing import Protocol

from sentinel_simulator.domain.models import (
    Credit,
    FaultSchedule,
    Order,
    Payment,
    ProviderEvent,
    Refund,
    RefundStats,
    SimulatorClock,
)


class Store(Protocol):
    def get_order(self, order_reference: str) -> Order | None: ...

    def list_payments(self, order_reference: str) -> list[Payment]: ...

    def get_payment(self, transaction_ref: str) -> Payment | None: ...

    def list_refunds(self, transaction_ref: str) -> list[Refund]: ...

    def get_refund(self, provider_ref: str) -> Refund | None: ...

    def put_refund(self, refund: Refund) -> None: ...

    def get_credit(self, provider_ref: str) -> Credit | None: ...

    def put_credit(self, credit: Credit) -> None: ...

    def get_stats(self, provider_ref: str) -> RefundStats: ...

    def put_stats(self, stats: RefundStats) -> None: ...

    def faults(self) -> FaultSchedule: ...

    def append_event(self, event: ProviderEvent) -> None: ...

    def list_events(self) -> list[ProviderEvent]: ...

    def clock(self) -> SimulatorClock: ...

    def replace_seed(
        self,
        *,
        orders: dict[str, Order],
        payments: dict[str, Payment],
        refunds: dict[str, Refund] | None = None,
    ) -> None: ...

    def reset_runtime(self) -> None: ...
