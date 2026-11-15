from __future__ import annotations

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


class InMemoryStore:
    def __init__(
        self,
        *,
        orders: dict[str, Order] | None = None,
        payments: dict[str, Payment] | None = None,
        refunds: dict[str, Refund] | None = None,
        clock: SimulatorClock | None = None,
    ) -> None:
        self._seed_orders = dict(orders or {})
        self._seed_payments = dict(payments or {})
        self._seed_refunds = dict(refunds or {})
        self._orders = dict(self._seed_orders)
        self._payments = dict(self._seed_payments)
        self._refunds: dict[str, Refund] = dict(self._seed_refunds)
        self._credits: dict[str, Credit] = {}
        self._stats: dict[str, RefundStats] = {}
        self._events: list[ProviderEvent] = []
        self._faults = FaultSchedule()
        self._clock = clock or SimulatorClock()
        self._clock_instant = self._clock.instant

    def get_order(self, order_reference: str) -> Order | None:
        return self._orders.get(order_reference)

    def list_payments(self, order_reference: str) -> list[Payment]:
        return [
            payment
            for payment in self._payments.values()
            if payment.order_reference == order_reference
        ]

    def get_payment(self, transaction_ref: str) -> Payment | None:
        return self._payments.get(transaction_ref)

    def list_refunds(self, transaction_ref: str) -> list[Refund]:
        return [
            refund for refund in self._refunds.values() if refund.transaction_ref == transaction_ref
        ]

    def get_refund(self, provider_ref: str) -> Refund | None:
        return self._refunds.get(provider_ref)

    def put_refund(self, refund: Refund) -> None:
        self._refunds[refund.provider_ref] = refund

    def get_credit(self, provider_ref: str) -> Credit | None:
        return self._credits.get(provider_ref)

    def put_credit(self, credit: Credit) -> None:
        self._credits[credit.provider_ref] = credit

    def get_stats(self, provider_ref: str) -> RefundStats:
        return self._stats.get(provider_ref) or RefundStats(provider_ref=provider_ref)

    def put_stats(self, stats: RefundStats) -> None:
        self._stats[stats.provider_ref] = stats

    def faults(self) -> FaultSchedule:
        return self._faults

    def append_event(self, event: ProviderEvent) -> None:
        self._events.append(event)

    def list_events(self) -> list[ProviderEvent]:
        return list(self._events)

    def clock(self) -> SimulatorClock:
        return self._clock

    def replace_seed(
        self,
        *,
        orders: dict[str, Order],
        payments: dict[str, Payment],
        refunds: dict[str, Refund] | None = None,
    ) -> None:
        self._seed_orders = dict(orders)
        self._seed_payments = dict(payments)
        self._seed_refunds = dict(refunds or {})
        self.reset_runtime()

    def reset_runtime(self) -> None:
        """Restore seeded fixtures; clear ephemeral refunds/credits/events/faults."""
        self._orders = dict(self._seed_orders)
        self._payments = dict(self._seed_payments)
        self._refunds = dict(self._seed_refunds)
        self._credits = {}
        self._stats = {}
        self._events = []
        self._faults.reset()
        # Demo reset keeps the configured clock mode (fixed instant or real time).
        self._clock = SimulatorClock(instant=self._clock_instant)
