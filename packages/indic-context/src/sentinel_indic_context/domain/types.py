"""Wire-aligned value objects for indic-context.v1 (ModelRequest/ModelResult)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa"
PORT = "indic-context.v1"

ALLOWED_ACTIONS = frozenset(
    {
        "STATUS_UPDATE",
        "OPEN_DISPUTE",
        "SCHEDULE_RECHECK",
        "REQUEST_REFUND",
        "SYNC_ORDER",
        "ESCALATE",
    }
)

MODEL_OUTCOMES = ("PROPOSAL", "NEEDS_INPUT", "ESCALATE")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Principal(StrictModel):
    principal_id: str
    tenant_id: str
    roles: list[str]
    subject_refs: list[str]
    case_ids: list[str]


class CaseMessage(StrictModel):
    message_id: str
    text: str
    language: str
    author: Literal["CUSTOMER", "OPERATOR"]
    occurred_at: str


class CaseInput(StrictModel):
    case_id: str
    case_revision: int = Field(ge=1)
    original_text: str
    language: str
    order_reference: str
    messages: list[CaseMessage]


class Case(StrictModel):
    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    case_id: str
    revision: int = Field(ge=1)
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


class RefundAction(StrictModel):
    action: Literal["REQUEST_REFUND"] = "REQUEST_REFUND"
    case_id: str
    case_revision: int = Field(ge=1)
    transaction_ref: str
    amount_minor: int = Field(ge=1)
    currency: Literal["INR"] = "INR"
    destination: Literal["ORIGINAL_PAYMENT_ROUTE"] = "ORIGINAL_PAYMENT_ROUTE"
    evidence_ids: list[str] = Field(min_length=1)
    policy_version: str


class EscalateAction(StrictModel):
    action: Literal["ESCALATE"] = "ESCALATE"
    case_id: str
    case_revision: int = Field(ge=1)
    evidence_ids: list[str]
    policy_version: str
    reason_code: str
    owner_queue: Literal["PAYMENTS", "FRAUD", "SUPERVISOR"]


class StatusAction(StrictModel):
    action: Literal["STATUS_UPDATE"] = "STATUS_UPDATE"
    case_id: str
    case_revision: int = Field(ge=1)
    evidence_ids: list[str]
    policy_version: str
    message_code: Literal["WAITING", "NEEDS_INPUT", "ESCALATED", "VERIFIED"]


class DisputeAction(StrictModel):
    action: Literal["OPEN_DISPUTE"] = "OPEN_DISPUTE"
    case_id: str
    case_revision: int = Field(ge=1)
    evidence_ids: list[str]
    policy_version: str
    transaction_ref: str
    reason_code: str


class RecheckAction(StrictModel):
    action: Literal["SCHEDULE_RECHECK"] = "SCHEDULE_RECHECK"
    case_id: str
    case_revision: int = Field(ge=1)
    evidence_ids: list[str]
    policy_version: str
    available_at: str
    reason_code: str


class SyncAction(StrictModel):
    action: Literal["SYNC_ORDER"] = "SYNC_ORDER"
    case_id: str
    case_revision: int = Field(ge=1)
    evidence_ids: list[str]
    policy_version: str
    transaction_ref: str
    order_reference: str


Action = RefundAction | EscalateAction | StatusAction | DisputeAction | RecheckAction | SyncAction


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


class NormalizedComplaint(StrictModel):
    """Derived claims only. Never mutates original_text or language."""

    language: str
    code_mixed: bool
    original_text: str
    reported_amount_minor: int | None = None
    currency: Literal["INR"] | None = None
    reported_payment_count: int | None = None
    reported_order_count: int | None = None
    negation_present: bool = False
    candidate_transaction_refs: list[str] = Field(default_factory=list)
    amount_ambiguous: bool = False
    reason_codes: list[str] = Field(default_factory=list)


class InferenceReport(StrictModel):
    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    port: Literal["indic-context.v1"] = PORT
    evidence_mode: Literal["fake-inference", "provider-observation"]
    model_id: str
    latency_ms: int = Field(ge=0)
    cost_units: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    native_review_limit: str
    outcome: Literal["PROPOSAL", "NEEDS_INPUT", "ESCALATE"]
    reason_codes: list[str]
