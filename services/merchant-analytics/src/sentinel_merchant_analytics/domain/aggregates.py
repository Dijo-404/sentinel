"""Deterministic merchant metric aggregates. Integer money; no floats for amounts."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from .types import (
    AGING_BUCKETS,
    RESOLVED_STATUSES,
    CaseRecord,
    MerchantMetrics,
    RefundFact,
)


def parse_rfc3339(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def format_exception_rate(exceptions: int, total: int) -> str:
    """Fixed 4-decimal fraction string; '0.0000' when total is zero."""
    if total <= 0:
        return "0.0000"
    # Integer arithmetic: rate * 10000 rounded half-up, then format.
    scaled = (exceptions * 10000 + total // 2) // total
    whole, frac = divmod(scaled, 10000)
    return f"{whole}.{frac:04d}"


def aging_bucket(age_seconds: int) -> str:
    if age_seconds < 24 * 3600:
        return "0-24h"
    if age_seconds < 3 * 24 * 3600:
        return "1-3d"
    if age_seconds < 7 * 24 * 3600:
        return "3-7d"
    return "7d+"


def median_int(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    # Even count: lower middle (deterministic; avoids float mean).
    return ordered[mid - 1]


def is_exception_case(case: CaseRecord, refunds: list[RefundFact]) -> bool:
    if case.status not in RESOLVED_STATUSES:
        return True
    return any(r.case_id == case.case_id and r.status == "PENDING" for r in refunds)


def compute_metrics(
    *,
    tenant_id: str,
    merchant_ref: str,
    window_start: str,
    window_end: str,
    cases: list[CaseRecord],
    refunds: list[RefundFact],
) -> MerchantMetrics:
    window_start_dt = parse_rfc3339(window_start)
    window_end_dt = parse_rfc3339(window_end)
    if window_end_dt < window_start_dt:
        raise ValueError("window_end must be >= window_start")

    in_window: list[CaseRecord] = []
    for case in cases:
        if case.merchant_ref != merchant_ref:
            continue
        opened = parse_rfc3339(case.opened_at)
        if window_start_dt <= opened <= window_end_dt:
            in_window.append(case)

    case_ids = {c.case_id for c in in_window}
    scoped_refunds = [r for r in refunds if r.case_id in case_ids]

    exceptions = sum(1 for c in in_window if is_exception_case(c, scoped_refunds))
    total = len(in_window)

    pending = [r for r in scoped_refunds if r.status == "PENDING"]
    unresolved_minor = sum(r.amount_minor for r in pending)
    currency = "INR"
    if in_window:
        currency = in_window[0].currency
    elif pending:
        currency = pending[0].currency

    buckets = {name: 0 for name in AGING_BUCKETS}
    for refund in pending:
        age = int((window_end_dt - parse_rfc3339(refund.observed_at)).total_seconds())
        if age < 0:
            age = 0
        buckets[aging_bucket(age)] += 1

    handling: list[int] = []
    for case in in_window:
        if case.status not in RESOLVED_STATUSES or not case.closed_at:
            continue
        seconds = int(
            (parse_rfc3339(case.closed_at) - parse_rfc3339(case.opened_at)).total_seconds()
        )
        if seconds >= 0:
            handling.append(seconds)

    cause_counts = Counter(c.intent for c in in_window if c.intent)
    top_causes = tuple(cause for cause, _ in cause_counts.most_common(5))

    return MerchantMetrics(
        tenant_id=tenant_id,
        merchant_ref=merchant_ref,
        window_start=window_start,
        window_end=window_end,
        exception_rate=format_exception_rate(exceptions, total),
        unresolved_minor=unresolved_minor,
        currency=currency,
        refund_aging_buckets=buckets,
        median_handling_seconds=median_int(handling),
        top_causes=top_causes,
    )
