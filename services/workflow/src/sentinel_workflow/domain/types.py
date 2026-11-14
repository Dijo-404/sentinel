"""Wire-aligned value objects for workflow.v1 and consumed peers."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "sentinel.task-contracts.v1"

CASE_STATES = (
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
)

WORKFLOW_EVENTS = ("START", "INPUT", "DECISION", "RECHECK")
MODEL_OUTCOMES = ("PROPOSAL", "NEEDS_INPUT", "ESCALATE")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Principal(StrictModel):
    principal_id: str
    tenant_id: str
    roles: list[str]
    subject_refs: list[str]
    case_ids: list[str]


class WorkflowRequest(StrictModel):
    case_id: str
    case_revision: int = Field(ge=1)
    job_key: str
    event: Literal["START", "INPUT", "DECISION", "RECHECK"]


class Ack(StrictModel):
    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    job_id: str
    accepted: Literal[True] = True


class CaseMessage(StrictModel):
    message_id: str
    text: str
    language: str
    author: Literal["CUSTOMER", "OPERATOR"]
    occurred_at: str


class CaseInput(StrictModel):
    case_id: str
    case_revision: int
    original_text: str
    language: str
    order_reference: str
    messages: list[CaseMessage]


class Case(StrictModel):
    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    case_id: str
    revision: int
    status: str
    language: str
    intent: str
    evidence_ids: list[str]
    action_id: str | None = None


class Evidence(StrictModel):
    evidence_id: str
    case_id: str
    source: str
    subject_ref: str
    observed_at: str
    expires_at: str
    digest: str
    verification_status: Literal["VERIFIED", "UNVERIFIED", "CONFLICTING"]
    facts: dict[str, Any]


class EvidenceBundle(StrictModel):
    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    case_id: str
    evidence: list[Evidence]
    reconciliation_codes: list[str]


class RefundAction(StrictModel):
    action: Literal["REQUEST_REFUND"] = "REQUEST_REFUND"
    case_id: str
    case_revision: int
    transaction_ref: str
    amount_minor: int = Field(ge=1)
    currency: Literal["INR"] = "INR"
    destination: Literal["ORIGINAL_PAYMENT_ROUTE"] = "ORIGINAL_PAYMENT_ROUTE"
    evidence_ids: list[str] = Field(min_length=1)
    policy_version: str


class EscalateAction(StrictModel):
    action: Literal["ESCALATE"] = "ESCALATE"
    case_id: str
    case_revision: int
    evidence_ids: list[str]
    policy_version: str
    reason_code: str
    owner_queue: Literal["PAYMENTS", "FRAUD", "SUPERVISOR"]


class StatusAction(StrictModel):
    action: Literal["STATUS_UPDATE"] = "STATUS_UPDATE"
    case_id: str
    case_revision: int
    evidence_ids: list[str]
    policy_version: str
    message_code: Literal["WAITING", "NEEDS_INPUT", "ESCALATED", "VERIFIED"]


Action = RefundAction | EscalateAction | StatusAction


class Approval(StrictModel):
    approval_id: str
    action_digest: str
    case_revision: int
    policy_version: str
    decision: Literal["APPROVE", "REJECT"]
    reviewer_id: str
    expires_at: str


class PolicyRequest(StrictModel):
    payload: dict[str, Any]
    evidence: list[Evidence]
    approval: Approval | None = None


class PolicyResult(StrictModel):
    outcome: Literal["ALLOW", "REQUIRE_APPROVAL", "DENY", "NEED_EVIDENCE"]
    reason_codes: list[str]
    policy_version: str
    action_digest: str
    required_evidence: list[str]


class ProposalRequest(StrictModel):
    operation_key: str
    payload: RefundAction
    action_digest: str
    # Top-level identity for ledger restart fallbacks; not part of action digest.
    order_reference: str | None = None


class ReservationRequest(StrictModel):
    operation_key: str
    payload: RefundAction
    action_digest: str
    approval_id: str
    # Required for reserve after approval — ledger rejects missing/blank.
    order_reference: str


class ActionRecord(StrictModel):
    action_id: str
    provider_ref: str
    payload: RefundAction
    action_digest: str
    status: str
    approval: Approval | None = None


class ModelRequest(StrictModel):
    case: Case
    input: CaseInput
    evidence: list[Evidence]


class ModelResult(StrictModel):
    outcome: Literal["PROPOSAL", "NEEDS_INPUT", "ESCALATE"]
    proposal: dict[str, Any] | None = None
    reason_codes: list[str]
    original_text: str
    language: str


class CaseResult(StrictModel):
    event_key: str
    expected_revision: int
    status: str
    evidence_ids: list[str]
    reason_code: str
    action_id: str | None = None
    assessment_id: str | None = None


class VerificationRequest(StrictModel):
    case_id: str
    case_revision: int
    action_id: str
    provider_ref: str


class VerificationResult(StrictModel):
    assessment_id: str
    case_id: str
    case_revision: int
    action_id: str
    assessed_at: str
    expires_at: str
    status: Literal["WAITING", "VERIFIED", "CONFLICT", "ESCALATED"]
    evidence: list[Evidence]
    reason_codes: list[str]


class ErrorBody(StrictModel):
    code: str
    message: str
    request_id: str


class RiskResumeRequest(StrictModel):
    """Clearance signal from risk.v1. Never carries financial approval."""

    event_type: str
    investigation_id: str
    case_id: str
    restriction_id: str
    tenant_id: str
    financial_approval_granted: bool = False


class CaseBlocks(StrictModel):
    case_id: str
    blocks_financial_actions: bool
    financial_approval_granted: Literal[False] = False
