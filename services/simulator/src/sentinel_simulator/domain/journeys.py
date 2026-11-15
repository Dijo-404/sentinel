from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sentinel_simulator.domain.models import Order, Payment, Refund

SANDBOX_TENANT_ID = "tenant-demo"
SUBJECT_REF = "subject-demo-42"
MERCHANT_REF = "merchant-demo-1"
AMOUNT_MINOR = 150_000
PAYTM_SUBJECT_REF = "subject-paytm-staging"
PAYTM_MERCHANT_REF = "merchant-paytm-staging"
PAYTM_AMOUNT_MINOR = 1_000

JOURNEY_PACKS = (
    "pending",
    "merchant_mismatch",
    "duplicate_payment",
    "refund_pending",
)
# Opt-in via POST /v1/admin/seeds/paytm_staging — not merged into default sandbox seed.
OPTIONAL_PACKS = ("paytm_staging",)

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
        merchant_ref=MERCHANT_REF,
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
        merchant_ref=MERCHANT_REF,
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
            merchant_ref=MERCHANT_REF,
        ),
        Payment(
            transaction_ref="TXN-B",
            order_reference="DEMO-ORDER-42",
            subject_ref=SUBJECT_REF,
            status="CAPTURED",
            amount_minor=AMOUNT_MINOR,
            currency="INR",
            merchant_ref=MERCHANT_REF,
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
        merchant_ref=MERCHANT_REF,
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


def _paytm_staging_pack() -> SeedSnapshot:
    """Paytm-shaped replay pack.

    Successful payments/refunds are synthetic-simulator until an initiate-capable
    staging MID can capture TXN_SUCCESS. Failed/missing order ids mirror live
    staging status observations (resultCode 334).
    """
    fixtures = Path(__file__).resolve().parents[3] / "fixtures" / "paytm_staging" / "seed_pack.json"
    if fixtures.is_file():
        payload = json.loads(fixtures.read_text(encoding="utf-8"))
        orders = {
            item["order_reference"]: Order(
                order_reference=str(item["order_reference"]),
                subject_ref=str(item["subject_ref"]),
                fulfilled_order_count=int(item["fulfilled_order_count"]),
                merchant_confirmed_duplicate=bool(item["merchant_confirmed_duplicate"]),
                paid=bool(item["paid"]),
            )
            for item in payload.get("orders", [])
        }
        payments = {
            item["transaction_ref"]: Payment(
                transaction_ref=str(item["transaction_ref"]),
                order_reference=str(item["order_reference"]),
                subject_ref=str(item["subject_ref"]),
                status=item["status"],
                amount_minor=int(item["amount_minor"]),
                currency=item["currency"],
                merchant_ref=str(item["merchant_ref"]),
            )
            for item in payload.get("payments", [])
        }
        refunds = {
            item["provider_ref"]: Refund(
                action_id=str(item["action_id"]),
                provider_ref=str(item["provider_ref"]),
                transaction_ref=str(item["transaction_ref"]),
                amount_minor=int(item["amount_minor"]),
                currency=item["currency"],
                status=item["status"],
            )
            for item in payload.get("refunds", [])
        }
        return SeedSnapshot(orders=orders, payments=payments, refunds=refunds)

    order = Order(
        order_reference="PAYTM-ORDER-A",
        subject_ref=PAYTM_SUBJECT_REF,
        fulfilled_order_count=1,
        merchant_confirmed_duplicate=True,
        paid=True,
    )
    payments = (
        Payment(
            transaction_ref="PAYTM-TXN-A1",
            order_reference=order.order_reference,
            subject_ref=PAYTM_SUBJECT_REF,
            status="CAPTURED",
            amount_minor=PAYTM_AMOUNT_MINOR,
            currency="INR",
            merchant_ref=PAYTM_MERCHANT_REF,
        ),
        Payment(
            transaction_ref="PAYTM-TXN-A2",
            order_reference=order.order_reference,
            subject_ref=PAYTM_SUBJECT_REF,
            status="CAPTURED",
            amount_minor=PAYTM_AMOUNT_MINOR,
            currency="INR",
            merchant_ref=PAYTM_MERCHANT_REF,
        ),
    )
    return SeedSnapshot(
        orders={order.order_reference: order},
        payments={payment.transaction_ref: payment for payment in payments},
        refunds={},
    )


_PACK_BUILDERS = {
    "pending": _pending_pack,
    "merchant_mismatch": _merchant_mismatch_pack,
    "duplicate_payment": _duplicate_payment_pack,
    "refund_pending": _refund_pending_pack,
    "paytm_staging": _paytm_staging_pack,
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
