from __future__ import annotations

from sentinel_simulator.domain.journeys import (
    AMOUNT_MINOR,
    FAULT_SCHEDULES,
    JOURNEY_PACKS,
    SANDBOX_TENANT_ID,
    SUBJECT_REF,
    SeedSnapshot,
    build_seed_pack,
    default_seed,
    merge_seed_packs,
)
from sentinel_simulator.domain.models import Order, Payment, Refund

__all__ = [
    "AMOUNT_MINOR",
    "DEMO_ORDER",
    "DEMO_PAYMENTS",
    "FAULT_SCHEDULES",
    "JOURNEY_PACKS",
    "SANDBOX_TENANT_ID",
    "SUBJECT_REF",
    "SeedSnapshot",
    "build_seed_pack",
    "default_seed",
    "demo_orders",
    "demo_payments",
    "demo_refunds",
    "merge_seed_packs",
]


def demo_orders() -> dict[str, Order]:
    return dict(default_seed().orders)


def demo_payments() -> dict[str, Payment]:
    return dict(default_seed().payments)


def demo_refunds() -> dict[str, Refund]:
    return dict(default_seed().refunds)


DEMO_ORDER = build_seed_pack("duplicate_payment").orders["DEMO-ORDER-42"]
DEMO_PAYMENTS = tuple(build_seed_pack("duplicate_payment").payments.values())
