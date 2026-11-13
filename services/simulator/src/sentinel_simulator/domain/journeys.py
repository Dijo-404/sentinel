from __future__ import annotations

from dataclasses import dataclass

from sentinel_simulator.domain.models import Order, Payment, Refund

SANDBOX_TENANT_ID = "tenant-demo"
SUBJECT_REF = "subject-demo-42"
AMOUNT_MINOR = 150_000

JOURNEY_PACKS = (
    "pending",
    "merchant_mismatch",
    "duplicate_payment",
    "refund_pending",
)

FAULT_SCHEDULES = {
    "timeout-after-accept": {
        "timeout_after_accept": True,
        "duplicate_events": False,
        "out_of_order_credit": False,
        "outage": False,
        "delay_ms": 0,
    },
    "duplicate-webhook": {
        "timeout_after_accept": False,
        "duplicate_events": True,
        "out_of_order_credit": False,
        "outage": False,
        "delay_ms": 0,
    },
    "out-of-order": {
        "timeout_after_accept": False,
        "duplicate_events": False,
        "out_of_order_credit": True,
        "outage": False,
        "delay_ms": 0,
    },
}


@dataclass(frozen=True)
class SeedSnapshot:
    orders: dict[str, Order]
    payments: dict[str, Payment]
    refunds: dict[str, Refund]


def _pending_pack() -> SeedSnapshot:
    order = Order(
        order_reference="JOURNEY-PENDING",
        subject_ref=SUBJECT_REF,
        fulfilled_order_count=0,
        merchant_confirmed_duplicate=False,
        paid=False,
    )
    payment = Payment(
        transaction_ref="TXN-PENDING",
        order_reference="JOURNEY-PENDING",
        subject_ref=SUBJECT_REF,
        status="PENDING",
        amount_minor=AMOUNT_MINOR,
        currency="INR",
    )
    return SeedSnapshot(
        orders={order.order_reference: order},
        payments={payment.transaction_ref: payment},
        refunds={},
    )


def _merchant_mismatch_pack() -> SeedSnapshot:
    order = Order(
        order_reference="JOURNEY-MISMATCH",
        subject_ref=SUBJECT_REF,
        fulfilled_order_count=0,
        merchant_confirmed_duplicate=False,
        paid=False,
    )
    payment = Payment(
        transaction_ref="TXN-MISMATCH",
        order_reference="JOURNEY-MISMATCH",
        subject_ref=SUBJECT_REF,
        status="CAPTURED",
        amount_minor=AMOUNT_MINOR,
        currency="INR",
    )
    return SeedSnapshot(
        orders={order.order_reference: order},
        payments={payment.transaction_ref: payment},
        refunds={},
    )


def _duplicate_payment_pack() -> SeedSnapshot:
    order = Order(
        order_reference="DEMO-ORDER-42",
        subject_ref=SUBJECT_REF,
        fulfilled_order_count=1,
        merchant_confirmed_duplicate=True,
        paid=True,
    )
    payments = (
        Payment(
            transaction_ref="TXN-A",
            order_reference="DEMO-ORDER-42",
            subject_ref=SUBJECT_REF,
            status="CAPTURED",
            amount_minor=AMOUNT_MINOR,
            currency="INR",
        ),
        Payment(
            transaction_ref="TXN-B",
            order_reference="DEMO-ORDER-42",
            subject_ref=SUBJECT_REF,
            status="CAPTURED",
            amount_minor=AMOUNT_MINOR,
            currency="INR",
        ),
    )
    return SeedSnapshot(
        orders={order.order_reference: order},
        payments={payment.transaction_ref: payment for payment in payments},
        refunds={},
    )


def _refund_pending_pack() -> SeedSnapshot:
    order = Order(
        order_reference="JOURNEY-REFUND-PENDING",
        subject_ref=SUBJECT_REF,
        fulfilled_order_count=1,
        merchant_confirmed_duplicate=False,
        paid=True,
    )
    payment = Payment(
        transaction_ref="TXN-REFUND-PENDING",
        order_reference="JOURNEY-REFUND-PENDING",
        subject_ref=SUBJECT_REF,
        status="CAPTURED",
        amount_minor=AMOUNT_MINOR,
        currency="INR",
    )
    refund = Refund(
        action_id="action-refund-pending-1",
        provider_ref="refund-pending-1",
        transaction_ref="TXN-REFUND-PENDING",
        amount_minor=AMOUNT_MINOR,
        currency="INR",
        status="PENDING",
    )
    return SeedSnapshot(
        orders={order.order_reference: order},
        payments={payment.transaction_ref: payment},
        refunds={refund.provider_ref: refund},
    )


_PACK_BUILDERS = {
    "pending": _pending_pack,
    "merchant_mismatch": _merchant_mismatch_pack,
    "duplicate_payment": _duplicate_payment_pack,
    "refund_pending": _refund_pending_pack,
}


def build_seed_pack(name: str) -> SeedSnapshot:
    builder = _PACK_BUILDERS.get(name)
    if builder is None:
        raise KeyError(name)
    return builder()


def merge_seed_packs(names: tuple[str, ...] = JOURNEY_PACKS) -> SeedSnapshot:
    orders: dict[str, Order] = {}
    payments: dict[str, Payment] = {}
    refunds: dict[str, Refund] = {}
    for name in names:
        pack = build_seed_pack(name)
        orders.update(pack.orders)
        payments.update(pack.payments)
        refunds.update(pack.refunds)
    return SeedSnapshot(orders=orders, payments=payments, refunds=refunds)


def default_seed() -> SeedSnapshot:
    return merge_seed_packs(JOURNEY_PACKS)
