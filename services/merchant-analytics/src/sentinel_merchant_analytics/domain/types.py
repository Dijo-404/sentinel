"""Framework-free wire-aligned types for merchant-analytics.v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"

RESOLVED_STATUSES = frozenset({"VERIFIED_RESOLVED", "CLOSED_NO_ACTION"})
AGING_BUCKETS = ("0-24h", "1-3d", "3-7d", "7d+")


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]
    merchant_refs: tuple[str, ...]

    def allows_merchant(self, merchant_ref: str) -> bool:
        """Empty merchant_refs deny; '*' grants all merchants in tenant."""
        if "*" in self.merchant_refs:
            return True
        return merchant_ref in self.merchant_refs

    def allows_case(self, case_id: str) -> bool:
        if "*" in self.case_ids:
            return True
        return case_id in self.case_ids


@dataclass(frozen=True, slots=True)
class CaseRecord:
    """Task-local case projection used for merchant analytics (read-only)."""

    case_id: str
    merchant_ref: str
    status: str
    intent: str
    opened_at: str
    closed_at: str | None
    evidence_ids: tuple[str, ...]
    currency: Literal["INR"] = "INR"


@dataclass(frozen=True, slots=True)
class RefundFact:
    case_id: str
    amount_minor: int
    currency: Literal["INR"]
    status: Literal["PENDING", "PROVIDER_CONFIRMED", "FAILED_FINAL"]
    observed_at: str


@dataclass(frozen=True, slots=True)
class MerchantMetrics:
    tenant_id: str
    merchant_ref: str
    window_start: str
    window_end: str
    exception_rate: str
    unresolved_minor: int
    currency: str
    refund_aging_buckets: dict[str, int]
    median_handling_seconds: int
    top_causes: tuple[str, ...]

    def to_wire(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "merchant_ref": self.merchant_ref,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "exception_rate": self.exception_rate,
            "unresolved_minor": self.unresolved_minor,
            "currency": self.currency,
            "refund_aging_buckets": dict(self.refund_aging_buckets),
            "median_handling_seconds": self.median_handling_seconds,
            "top_causes": list(self.top_causes),
        }
