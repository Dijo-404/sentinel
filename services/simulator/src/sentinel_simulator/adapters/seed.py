from __future__ import annotations

from sentinel_simulator.domain.models import Order, Payment

DEMO_ORDER = Order(
    order_reference="DEMO-ORDER-42",
    subject_ref="subject-demo-42",
    fulfilled_order_count=1,
    merchant_confirmed_duplicate=True,
    paid=True,
)

DEMO_PAYMENTS = (
    Payment(
        transaction_ref="TXN-A",
        order_reference="DEMO-ORDER-42",
        subject_ref="subject-demo-42",
        status="CAPTURED",
        amount_minor=150000,
        currency="INR",
    ),
    Payment(
        transaction_ref="TXN-B",
        order_reference="DEMO-ORDER-42",
        subject_ref="subject-demo-42",
        status="CAPTURED",
        amount_minor=150000,
        currency="INR",
    ),
)


def demo_orders() -> dict[str, Order]:
    return {DEMO_ORDER.order_reference: DEMO_ORDER}


def demo_payments() -> dict[str, Payment]:
    return {payment.transaction_ref: payment for payment in DEMO_PAYMENTS}
