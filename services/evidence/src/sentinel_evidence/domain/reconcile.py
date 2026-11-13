"""Deterministic reconciliation over payment, order and refund facts."""

from __future__ import annotations

from datetime import datetime

from .types import Evidence, Order, Payment, Refund, VerificationStatus


def parse_rfc3339(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def classify_verification(
    *,
    expires_at: str,
    now: datetime,
    conflicting: bool,
) -> VerificationStatus:
    if conflicting:
        return "CONFLICTING"
    if parse_rfc3339(expires_at) <= now:
        return "UNVERIFIED"
    return "VERIFIED"


def reconcile_codes(
    *,
    payments: tuple[Payment, ...],
    order: Order,
    refunds: tuple[Refund, ...],
    stale: bool,
    conflicting: bool,
) -> tuple[str, ...]:
    codes: list[str] = []
    captured = [p for p in payments if p.status == "CAPTURED"]
    refs = {p.transaction_ref for p in captured}
    amounts = {p.amount_minor for p in captured}

    if stale:
        codes.append("STALE_PROVIDER_SNAPSHOT")
    if conflicting:
        codes.append("CONFLICTING_PAYMENT_RECORD")

    subject_mismatch = any(p.subject_ref != order.subject_ref for p in payments)
    if subject_mismatch:
        codes.append("CONFLICTING_SUBJECT")

    if len(refs) >= 2:
        codes.append("DISTINCT_TRANSACTION_REFS")
    if order.merchant_confirmed_duplicate:
        codes.append("MERCHANT_CONFIRMED_DUPLICATE")
    if len(captured) > order.fulfilled_order_count:
        codes.append("ORDER_UNDERFULFILLED")

    # Equal amounts alone never prove duplication.
    if len(captured) >= 2 and len(amounts) == 1 and "DUPLICATE_PAYMENT" not in codes:
        has_independent = (
            "DISTINCT_TRANSACTION_REFS" in codes
            and "MERCHANT_CONFIRMED_DUPLICATE" in codes
            and "ORDER_UNDERFULFILLED" in codes
        )
        if has_independent:
            codes.append("DUPLICATE_PAYMENT")
        else:
            codes.append("EQUAL_AMOUNTS_INSUFFICIENT")

    for refund in refunds:
        if refund.status == "PENDING" and "REFUND_PENDING" not in codes:
            codes.append("REFUND_PENDING")
        elif refund.status == "PROVIDER_CONFIRMED" and "REFUND_PROVIDER_CONFIRMED" not in codes:
            codes.append("REFUND_PROVIDER_CONFIRMED")
        elif refund.status == "FAILED_FINAL" and "REFUND_FAILED_FINAL" not in codes:
            codes.append("REFUND_FAILED_FINAL")

    return tuple(codes)


def apply_status(
    evidence: tuple[Evidence, ...], status: VerificationStatus
) -> tuple[Evidence, ...]:
    return tuple(
        Evidence(
            evidence_id=item.evidence_id,
            case_id=item.case_id,
            source=item.source,
            subject_ref=item.subject_ref,
            observed_at=item.observed_at,
            expires_at=item.expires_at,
            digest=item.digest,
            verification_status=status,
            facts=item.facts,
            payload_utf8=item.payload_utf8,
        )
        for item in evidence
    )
