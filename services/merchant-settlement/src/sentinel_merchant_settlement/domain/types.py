"""Wire-aligned domain types for merchant-settlement.v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
COMPONENT = "merchant-settlement"
PORT = "merchant-settlement.v1"

FindingKind = Literal[
    "MISSING_PAYMENT",
    "MISSING_SETTLEMENT",
    "DUPLICATE_ROW",
    "FEE_DIFF",
    "SHORT_SETTLE",
    "UNMATCHED_ORDER",
]
FindingStatus = Literal["OPEN", "ASSIGNED", "ESCALATED", "CLOSED"]
PaymentStatus = Literal["CAPTURED", "PENDING", "FAILED"]


@dataclass(frozen=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]

    def allows_merchant(self, merchant_ref: str) -> bool:
        if "merchant:*" in self.subject_refs or "*" in self.subject_refs:
            return True
        return f"merchant:{merchant_ref}" in self.subject_refs


@dataclass(frozen=True)
class SettlementRow:
    row_id: str
    transaction_ref: str
    settled_minor: int
    fee_minor: int
    occurred_at: str
    order_ref: str | None = None


@dataclass(frozen=True)
class SettlementBatch:
    batch_id: str
    tenant_id: str
    merchant_ref: str
    period_start: str
    period_end: str
    currency: str
    rows: tuple[SettlementRow, ...]
    source_digest: str


@dataclass
class SettlementFinding:
    finding_id: str
    batch_id: str
    kind: FindingKind
    evidence_ids: list[str]
    status: FindingStatus = "OPEN"
    transaction_ref: str | None = None
    expected_minor: int | None = None
    observed_minor: int | None = None
    assignee: str | None = None

    def as_dict(self) -> dict:
        out: dict = {
            "finding_id": self.finding_id,
            "batch_id": self.batch_id,
            "kind": self.kind,
            "evidence_ids": list(self.evidence_ids),
            "status": self.status,
        }
        if self.transaction_ref is not None:
            out["transaction_ref"] = self.transaction_ref
        if self.expected_minor is not None:
            out["expected_minor"] = self.expected_minor
        if self.observed_minor is not None:
            out["observed_minor"] = self.observed_minor
        if self.assignee is not None:
            out["assignee"] = self.assignee
        return out


@dataclass(frozen=True)
class Payment:
    transaction_ref: str
    order_reference: str
    subject_ref: str
    status: PaymentStatus
    amount_minor: int
    currency: str
    expected_fee_minor: int = 0
    occurred_at: str = "2026-11-01T10:00:00Z"


@dataclass(frozen=True)
class Order:
    order_reference: str
    subject_ref: str
    fulfilled_order_count: int
    merchant_confirmed_duplicate: bool
    paid: bool


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    transaction_ref: str | None
    order_reference: str | None
    verification_status: str


@dataclass(frozen=True)
class PeerWorld:
    """Normalized peer facts used by reconciliation (fixture or HTTP-derived)."""

    payments: tuple[Payment, ...] = ()
    orders: tuple[Order, ...] = ()
    evidence: tuple[EvidenceRecord, ...] = ()

    def payment_by_ref(self) -> dict[str, Payment]:
        return {p.transaction_ref: p for p in self.payments}

    def order_by_ref(self) -> dict[str, Order]:
        return {o.order_reference: o for o in self.orders}

    def evidence_ids_for(
        self, *, transaction_ref: str | None = None, order_reference: str | None = None
    ) -> list[str]:
        ids: list[str] = []
        for item in self.evidence:
            if transaction_ref and item.transaction_ref == transaction_ref:
                ids.append(item.evidence_id)
            elif order_reference and item.order_reference == order_reference:
                ids.append(item.evidence_id)
        return ids


@dataclass
class ImportResult:
    batch: SettlementBatch
    findings: list[SettlementFinding] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "contract_version": CONTRACT_VERSION,
            "batch": batch_as_dict(self.batch),
            "findings": [f.as_dict() for f in self.findings],
        }


def batch_as_dict(batch: SettlementBatch) -> dict:
    rows = []
    for row in batch.rows:
        item = {
            "row_id": row.row_id,
            "transaction_ref": row.transaction_ref,
            "settled_minor": row.settled_minor,
            "fee_minor": row.fee_minor,
            "occurred_at": row.occurred_at,
        }
        if row.order_ref is not None:
            item["order_ref"] = row.order_ref
        rows.append(item)
    return {
        "batch_id": batch.batch_id,
        "tenant_id": batch.tenant_id,
        "merchant_ref": batch.merchant_ref,
        "period_start": batch.period_start,
        "period_end": batch.period_end,
        "currency": batch.currency,
        "rows": rows,
        "source_digest": batch.source_digest,
    }
