"""Framework-free wire-aligned types for risk.v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"
PORT_NAME = "risk.v1"

InvestigationStatus = Literal[
    "OPEN",
    "UNDER_REVIEW",
    "AWAITING_EVIDENCE",
    "CLOSED",
]
FindingClassification = Literal[
    "LEGITIMATE",
    "INSUFFICIENT_EVIDENCE",
    "SUSPICIOUS",
    "CONFIRMED_FRAUD",
]
RestrictionStatus = Literal["ACTIVE", "CLEARED", "MAINTAINED"]
RestrictionDecision = Literal["CLEAR", "MAINTAIN", "CONFIRM_FRAUD"]

FINDING_CLASSIFICATIONS = (
    "LEGITIMATE",
    "INSUFFICIENT_EVIDENCE",
    "SUSPICIOUS",
    "CONFIRMED_FRAUD",
)
RESTRICTION_DECISIONS = ("CLEAR", "MAINTAIN", "CONFIRM_FRAUD")


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]
    queue_refs: tuple[str, ...] = ()

    def allows_case(self, case_id: str) -> bool:
        if "*" in self.case_ids:
            return True
        return case_id in self.case_ids

    def allows_queue(self, queue_ref: str) -> bool:
        if "*" in self.queue_refs:
            return True
        if not self.queue_refs:
            return True
        return queue_ref in self.queue_refs

    def is_risk_officer(self) -> bool:
        return "risk_officer" in self.roles

    def is_workflow_service(self) -> bool:
        return "workflow" in self.roles


@dataclass(frozen=True, slots=True)
class CaseSnapshot:
    contract_version: str
    case_id: str
    revision: int
    status: str
    language: str
    intent: str
    evidence_ids: tuple[str, ...]
    escalation_destination: str | None = None


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    investigation_id: str
    classification: FindingClassification
    evidence_ids: tuple[str, ...]
    notes: str
    recorded_by: str
    recorded_at: str
    revision: int

    def to_wire(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "investigation_id": self.investigation_id,
            "classification": self.classification,
            "evidence_ids": list(self.evidence_ids),
            "notes": self.notes,
            "recorded_by": self.recorded_by,
            "recorded_at": self.recorded_at,
            "revision": self.revision,
        }


@dataclass(frozen=True, slots=True)
class RiskRestriction:
    restriction_id: str
    tenant_id: str
    case_id: str
    investigation_id: str
    reason_code: str
    status: RestrictionStatus
    blocks_financial_actions: bool
    created_at: str
    review_due_at: str
    created_by: str
    policy_version: str
    evidence_ids: tuple[str, ...]
    revision: int
    transaction_ref: str | None = None
    action_id: str | None = None
    cleared_by: str | None = None
    clearance_reason: str | None = None
    # Clearance never implies ledger approval. Always false on this record.
    financial_approval_granted: bool = False

    def to_wire(self) -> dict[str, Any]:
        return {
            "restriction_id": self.restriction_id,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "investigation_id": self.investigation_id,
            "reason_code": self.reason_code,
            "status": self.status,
            "blocks_financial_actions": self.blocks_financial_actions,
            "created_at": self.created_at,
            "review_due_at": self.review_due_at,
            "created_by": self.created_by,
            "policy_version": self.policy_version,
            "evidence_ids": list(self.evidence_ids),
            "revision": self.revision,
            "transaction_ref": self.transaction_ref,
            "action_id": self.action_id,
            "cleared_by": self.cleared_by,
            "clearance_reason": self.clearance_reason,
            "financial_approval_granted": False,
        }


@dataclass(frozen=True, slots=True)
class Investigation:
    investigation_id: str
    tenant_id: str
    case_id: str
    case_revision: int
    reason_code: str
    status: InvestigationStatus
    queue_ref: str
    owner_principal_id: str | None
    severity: str
    created_at: str
    updated_at: str
    revision: int
    finding_ids: tuple[str, ...]
    restriction_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...] = ()

    def to_wire(self) -> dict[str, Any]:
        return {
            "investigation_id": self.investigation_id,
            "tenant_id": self.tenant_id,
            "case_id": self.case_id,
            "case_revision": self.case_revision,
            "reason_code": self.reason_code,
            "status": self.status,
            "queue_ref": self.queue_ref,
            "owner_principal_id": self.owner_principal_id,
            "severity": self.severity,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "revision": self.revision,
            "finding_ids": list(self.finding_ids),
            "restriction_ids": list(self.restriction_ids),
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True, slots=True)
class DashboardView:
    open_investigations: int
    active_restrictions: int
    awaiting_evidence: int
    aging_investigations: int
    blocked_actions: int
    investigations: tuple[Investigation, ...]

    def to_wire(self) -> dict[str, Any]:
        return {
            "open_investigations": self.open_investigations,
            "active_restrictions": self.active_restrictions,
            "awaiting_evidence": self.awaiting_evidence,
            "aging_investigations": self.aging_investigations,
            "blocked_actions": self.blocked_actions,
            "investigations": [item.to_wire() for item in self.investigations],
        }


@dataclass(frozen=True, slots=True)
class CreateInvestigationRequest:
    case_id: str
    reason_code: str
    queue_ref: str = "FRAUD"
    severity: str = "MEDIUM"
    case_revision: int | None = None
    evidence_ids: tuple[str, ...] = ()
    review_due_at: str | None = None


@dataclass(frozen=True, slots=True)
class RecordFindingRequest:
    classification: FindingClassification
    evidence_ids: tuple[str, ...]
    notes: str = ""
    expected_revision: int | None = None


@dataclass(frozen=True, slots=True)
class RestrictionDecisionRequest:
    decision: RestrictionDecision
    reason: str
    expected_revision: int
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResumeEvent:
    """Durable resume signal for workflow/policy. Never a financial approval."""

    event_type: str
    investigation_id: str
    case_id: str
    restriction_id: str
    tenant_id: str
    financial_approval_granted: bool = False
