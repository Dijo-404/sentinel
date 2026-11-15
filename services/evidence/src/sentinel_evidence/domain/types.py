"""Framework-free wire-aligned types for evidence.v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"

VerificationStatus = Literal["VERIFIED", "UNVERIFIED", "CONFLICTING"]
PaymentStatus = Literal["CAPTURED", "PENDING", "FAILED"]
RefundStatus = Literal["PENDING", "PROVIDER_CONFIRMED", "FAILED_FINAL"]


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]

    def allows_case(self, case_id: str) -> bool:
        """Empty case_ids deny; '*' grants all cases."""
        if "*" in self.case_ids:
            return True
        return case_id in self.case_ids


@dataclass(frozen=True, slots=True)
class Payment:
    transaction_ref: str
    order_reference: str
    subject_ref: str
    status: PaymentStatus
    amount_minor: int
    currency: Literal["INR"]
    merchant_ref: str


@dataclass(frozen=True, slots=True)
class Order:
    order_reference: str
    subject_ref: str
    fulfilled_order_count: int
    merchant_confirmed_duplicate: bool
    paid: bool


@dataclass(frozen=True, slots=True)
class Refund:
    action_id: str
    provider_ref: str
    transaction_ref: str
    amount_minor: int
    currency: Literal["INR"]
    status: RefundStatus


@dataclass(frozen=True, slots=True)
class Credit:
    provider_ref: str
    confirmed: bool
    observed_at: str


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    case_id: str
    source: str
    subject_ref: str
    observed_at: str
    expires_at: str
    digest: str
    verification_status: VerificationStatus
    facts: dict[str, Any]
    payload_utf8: bytes = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    contract_version: str
    case_id: str
    evidence: tuple[Evidence, ...]
    reconciliation_codes: tuple[str, ...]

    def to_wire(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "case_id": self.case_id,
            "evidence": [
                {
                    "evidence_id": item.evidence_id,
                    "case_id": item.case_id,
                    "source": item.source,
                    "subject_ref": item.subject_ref,
                    "observed_at": item.observed_at,
                    "expires_at": item.expires_at,
                    "digest": item.digest,
                    "verification_status": item.verification_status,
                    "facts": item.facts,
                }
                for item in self.evidence
            ],
            "reconciliation_codes": list(self.reconciliation_codes),
        }


@dataclass(frozen=True, slots=True)
class CollectRequest:
    case_id: str
    case_revision: int
    order_reference: str


@dataclass(frozen=True, slots=True)
class ProviderSnapshot:
    """Raw peer responses retained as original UTF-8 bytes plus parsed facts."""

    payment_items: tuple[tuple[bytes, Payment], ...]
    order_payload: bytes
    order: Order
    refund_items: tuple[tuple[bytes, Refund], ...]
    observed_at: str
    expires_at: str

    @property
    def payments(self) -> tuple[Payment, ...]:
        return tuple(payment for _, payment in self.payment_items)

    @property
    def refunds(self) -> tuple[Refund, ...]:
        return tuple(refund for _, refund in self.refund_items)
