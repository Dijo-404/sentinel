"""Wire-aligned domain values. No framework imports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

CONTRACT_VERSION = "sentinel.task-contracts.v1"

CASE_STATES = frozenset(
    {
        "RECEIVED",
        "NEEDS_INPUT",
        "INVESTIGATING",
        "RECONCILING",
        "PLANNING",
        "POLICY_CHECK",
        "WAITING_APPROVAL",
        "EXECUTING",
        "VERIFYING",
        "WAITING_EXTERNAL",
        "ESCALATED",
        "VERIFIED_RESOLVED",
        "CLOSED_NO_ACTION",
    }
)

OWNER_QUEUES = frozenset({"PAYMENTS", "FRAUD", "SUPERVISOR"})
CHANNELS = frozenset({"web", "voice"})
ROLES = frozenset(
    {
        "customer",
        "operator",
        "supervisor",
        "workflow",
        "dispatcher",
        "verifier",
        "sandbox-admin",
    }
)


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...] = ()
    case_ids: tuple[str, ...] = ()

    def has_role(self, *wanted: str) -> bool:
        return bool(set(self.roles) & set(wanted))


@dataclass(frozen=True, slots=True)
class CaseCreate:
    message: str
    language: str
    order_reference: str
    channel: Literal["web", "voice"]


@dataclass(frozen=True, slots=True)
class CaseCreated:
    case_id: str
    status: Literal["RECEIVED"]
    status_url: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "status_url": self.status_url,
        }


@dataclass(frozen=True, slots=True)
class Case:
    case_id: str
    revision: int
    status: str
    language: str
    intent: str
    evidence_ids: tuple[str, ...]
    action_id: str | None = None
    assigned_principal_id: str | None = None
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contract_version": self.contract_version,
            "case_id": self.case_id,
            "revision": self.revision,
            "status": self.status,
            "language": self.language,
            "intent": self.intent,
            "evidence_ids": list(self.evidence_ids),
        }
        if self.action_id is not None:
            body["action_id"] = self.action_id
        if self.assigned_principal_id is not None:
            body["assigned_principal_id"] = self.assigned_principal_id
        return body


@dataclass(frozen=True, slots=True)
class CaseMessage:
    message_id: str
    text: str
    language: str
    author: Literal["CUSTOMER", "OPERATOR"]
    occurred_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "text": self.text,
            "language": self.language,
            "author": self.author,
            "occurred_at": self.occurred_at,
        }


@dataclass(frozen=True, slots=True)
class CaseInput:
    case_id: str
    case_revision: int
    original_text: str
    language: str
    order_reference: str
    messages: tuple[CaseMessage, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_revision": self.case_revision,
            "original_text": self.original_text,
            "language": self.language,
            "order_reference": self.order_reference,
            "messages": [m.to_dict() for m in self.messages],
        }


@dataclass(frozen=True, slots=True)
class CaseEvent:
    event_id: str
    sequence: int
    case_id: str
    case_revision: int
    type: str
    occurred_at: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "case_id": self.case_id,
            "case_revision": self.case_revision,
            "type": self.type,
            "occurred_at": self.occurred_at,
            "payload": self.payload,
        }


@dataclass(frozen=True, slots=True)
class CaseResult:
    event_key: str
    expected_revision: int
    status: str
    evidence_ids: tuple[str, ...]
    reason_code: str
    action_id: str | None = None
    assessment_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "event_key": self.event_key,
            "expected_revision": self.expected_revision,
            "status": self.status,
            "evidence_ids": list(self.evidence_ids),
            "reason_code": self.reason_code,
        }
        if self.action_id is not None:
            body["action_id"] = self.action_id
        if self.assessment_id is not None:
            body["assessment_id"] = self.assessment_id
        return body


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    decision: Literal["APPROVE", "REJECT"]
    action_digest: str
    case_revision: int
    policy_version: str
    expires_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "action_digest": self.action_digest,
            "case_revision": self.case_revision,
            "policy_version": self.policy_version,
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True, slots=True)
class Approval:
    approval_id: str
    action_digest: str
    case_revision: int
    policy_version: str
    decision: Literal["APPROVE", "REJECT"]
    reviewer_id: str
    expires_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "action_digest": self.action_digest,
            "case_revision": self.case_revision,
            "policy_version": self.policy_version,
            "decision": self.decision,
            "reviewer_id": self.reviewer_id,
            "expires_at": self.expires_at,
        }


@dataclass(frozen=True, slots=True)
class WorkflowRequest:
    case_id: str
    case_revision: int
    job_key: str
    event: Literal["START", "INPUT", "DECISION", "RECHECK"]
    # Intake identity for outbox/scheduling; wire POST /v1/runs omits this (see to_wire_dict).
    order_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "case_id": self.case_id,
            "case_revision": self.case_revision,
            "job_key": self.job_key,
            "event": self.event,
        }
        if self.order_reference is not None:
            data["order_reference"] = self.order_reference
        return data

    def to_wire_dict(self) -> dict[str, Any]:
        """workflow.v1 run body: order identity is loaded from CaseInput, not stripped here."""
        return {
            "case_id": self.case_id,
            "case_revision": self.case_revision,
            "job_key": self.job_key,
            "event": self.event,
        }


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    contract_version: str
    case_id: str
    evidence: tuple[dict[str, Any], ...]
    reconciliation_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "case_id": self.case_id,
            "evidence": list(self.evidence),
            "reconciliation_codes": list(self.reconciliation_codes),
        }


@dataclass(frozen=True, slots=True)
class VerificationResult:
    assessment_id: str
    case_id: str
    case_revision: int
    action_id: str
    assessed_at: str
    expires_at: str
    status: str
    evidence: tuple[dict[str, Any], ...]
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "case_id": self.case_id,
            "case_revision": self.case_revision,
            "action_id": self.action_id,
            "assessed_at": self.assessed_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "evidence": list(self.evidence),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True, slots=True)
class ErrorBody:
    code: str
    message: str
    request_id: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "request_id": self.request_id}


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 422,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
