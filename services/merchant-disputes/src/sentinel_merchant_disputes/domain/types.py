"""Framework-free wire-aligned types for merchant-disputes.v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"

DisputeStatus = Literal[
    "OPEN",
    "EVIDENCE_PENDING",
    "SUBMITTED",
    "WON",
    "LOST",
    "WITHDRAWN",
]
TerminalStatus = Literal["WON", "LOST", "WITHDRAWN"]

# Required kinds inside assembled packets before submission is allowed.
REQUIRED_EVIDENCE_KINDS = ("PAYMENT", "ORDER", "DELIVERY")


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]
    merchant_refs: tuple[str, ...]

    def allows_case(self, case_id: str) -> bool:
        if "*" in self.case_ids:
            return True
        return case_id in self.case_ids

    def allows_merchant(self, merchant_ref: str) -> bool:
        if "*" in self.merchant_refs:
            return True
        return merchant_ref in self.merchant_refs

    def is_operator(self) -> bool:
        return bool({"operator", "supervisor"} & set(self.roles))


@dataclass(frozen=True, slots=True)
class CaseSnapshot:
    contract_version: str
    case_id: str
    revision: int
    status: str
    language: str
    intent: str
    evidence_ids: tuple[str, ...]
    order_reference: str | None = None


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_id: str
    case_id: str
    source: str
    subject_ref: str
    observed_at: str
    expires_at: str
    digest: str
    verification_status: str
    facts: dict[str, Any]

    @property
    def kind(self) -> str | None:
        kind = self.facts.get("kind")
        return str(kind) if kind is not None else None


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    contract_version: str
    case_id: str
    evidence: tuple[EvidenceItem, ...]
    reconciliation_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidencePacket:
    packet_id: str
    dispute_id: str
    case_id: str
    evidence_ids: tuple[str, ...]
    kinds: tuple[str, ...]
    assembled_at: str


@dataclass(frozen=True, slots=True)
class DisputeCase:
    dispute_id: str
    tenant_id: str
    merchant_ref: str
    case_id: str
    reason_code: str
    deadline_at: str
    evidence_packet_ids: tuple[str, ...]
    status: DisputeStatus
    order_reference: str = ""
    case_revision: int = 1

    def to_wire(self) -> dict[str, Any]:
        return {
            "dispute_id": self.dispute_id,
            "tenant_id": self.tenant_id,
            "merchant_ref": self.merchant_ref,
            "case_id": self.case_id,
            "reason_code": self.reason_code,
            "deadline_at": self.deadline_at,
            "evidence_packet_ids": list(self.evidence_packet_ids),
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class CreateDisputeRequest:
    case_id: str
    merchant_ref: str
    reason_code: str
    deadline_at: str | None = None
    order_reference: str | None = None


@dataclass(frozen=True, slots=True)
class DeadlineView:
    dispute_id: str
    deadline_at: str
    overdue: bool
    status: DisputeStatus

    def to_wire(self) -> dict[str, Any]:
        return {
            "dispute_id": self.dispute_id,
            "deadline_at": self.deadline_at,
            "overdue": self.overdue,
            "status": self.status,
        }
