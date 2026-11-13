"""Local payment-provider.v1 doubles. Never imported from services/simulator."""

from __future__ import annotations

from dataclasses import dataclass, field

from sentinel_merchant_settlement.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_settlement.domain.types import Order, Payment, PeerWorld, Principal

CASE_VALID = "valid"
CASE_UNAVAILABLE = "unavailable"
CASE_MALFORMED = "malformed"
CASE_UNAUTHORIZED = "unauthorized_or_out_of_scope"


def demo_payments() -> tuple[Payment, ...]:
    return (
        Payment(
            transaction_ref="TXN-OK",
            order_reference="ORDER-OK",
            subject_ref="subj-demo-1",
            status="CAPTURED",
            amount_minor=150000,
            currency="INR",
            expected_fee_minor=5000,
            occurred_at="2026-11-02T10:00:00Z",
        ),
        Payment(
            transaction_ref="TXN-FEE",
            order_reference="ORDER-FEE",
            subject_ref="subj-demo-1",
            status="CAPTURED",
            amount_minor=150000,
            currency="INR",
            expected_fee_minor=5000,
            occurred_at="2026-11-02T11:00:00Z",
        ),
        Payment(
            transaction_ref="TXN-SHORT",
            order_reference="ORDER-SHORT",
            subject_ref="subj-demo-1",
            status="CAPTURED",
            amount_minor=150000,
            currency="INR",
            expected_fee_minor=5000,
            occurred_at="2026-11-02T12:00:00Z",
        ),
        Payment(
            transaction_ref="TXN-MISS-SETTLE",
            order_reference="ORDER-MISS-SETTLE",
            subject_ref="subj-demo-1",
            status="CAPTURED",
            amount_minor=99000,
            currency="INR",
            expected_fee_minor=1000,
            occurred_at="2026-11-03T09:00:00Z",
        ),
        Payment(
            transaction_ref="TXN-DUP",
            order_reference="ORDER-DUP",
            subject_ref="subj-demo-1",
            status="CAPTURED",
            amount_minor=50000,
            currency="INR",
            expected_fee_minor=500,
            occurred_at="2026-11-02T13:00:00Z",
        ),
        Payment(
            transaction_ref="TXN-UNMATCHED",
            order_reference="ORDER-REAL",
            subject_ref="subj-demo-1",
            status="CAPTURED",
            amount_minor=20000,
            currency="INR",
            expected_fee_minor=200,
            occurred_at="2026-11-02T14:00:00Z",
        ),
    )


def demo_orders() -> tuple[Order, ...]:
    return (
        Order("ORDER-OK", "subj-demo-1", 1, False, True),
        Order("ORDER-FEE", "subj-demo-1", 1, False, True),
        Order("ORDER-SHORT", "subj-demo-1", 1, False, True),
        Order("ORDER-MISS-SETTLE", "subj-demo-1", 1, False, True),
        Order("ORDER-DUP", "subj-demo-1", 1, False, True),
        Order("ORDER-REAL", "subj-demo-1", 1, False, True),
    )


@dataclass
class StubPaymentProvider:
    case: str = CASE_VALID
    payments: tuple[Payment, ...] = field(default_factory=demo_payments)
    orders: tuple[Order, ...] = field(default_factory=demo_orders)

    def load_world(
        self,
        *,
        principal: Principal,
        tenant_id: str,
        merchant_ref: str,
        period_start: str,
        period_end: str,
        order_refs: tuple[str, ...],
        transaction_refs: tuple[str, ...],
    ) -> PeerWorld:
        del order_refs, transaction_refs
        if self.case == CASE_UNAVAILABLE:
            raise PeerUnavailableError("Required peer unavailable")
        if self.case == CASE_MALFORMED:
            raise PeerMalformedError("Provider response failed schema validation")
        if self.case == CASE_UNAUTHORIZED:
            raise PeerUnauthorizedError("Provider denied scoped read")
        if principal.tenant_id != tenant_id:
            raise PeerUnauthorizedError("Provider denied scoped read")
        del merchant_ref, period_start, period_end
        return PeerWorld(payments=self.payments, orders=self.orders, evidence=())
