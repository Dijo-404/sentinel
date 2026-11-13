"""Wire-aligned value objects for merchant-refunds.v1 and consumed peers."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sentinel_merchant_refunds import CONTRACT_VERSION

RequestStatus = Literal[
    "DRAFT",
    "SUBMITTED",
    "AWAITING_APPROVAL",
    "RESERVED",
    "REJECTED",
    "VERIFIED",
    "FAILED",
]

LedgerActionStatus = Literal[
    "PROPOSED",
    "RESERVED",
    "DISPATCHING",
    "OUTCOME_UNKNOWN",
    "PENDING",
    "PROVIDER_CONFIRMED",
    "CREDIT_CONFIRMED",
    "FAILED_FINAL",
    "ESCALATED",
]

# Ledger statuses that prove customer credit. PENDING and PROVIDER_CONFIRMED do not.
CREDIT_VERIFIED_LEDGER_STATUSES = frozenset({"CREDIT_CONFIRMED"})

# Ledger statuses that mean the financial write failed finally.
FAILED_LEDGER_STATUSES = frozenset({"FAILED_FINAL"})


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Principal(StrictModel):
    principal_id: str
    tenant_id: str
    merchant_ref: str
    roles: list[str]


class RefundActionPayload(StrictModel):
    action: Literal["REQUEST_REFUND"] = "REQUEST_REFUND"
    case_id: str
    case_revision: int = Field(ge=1)
    transaction_ref: str
    amount_minor: int = Field(ge=1)
    currency: Literal["INR"] = "INR"
    destination: Literal["ORIGINAL_PAYMENT_ROUTE"] = "ORIGINAL_PAYMENT_ROUTE"
    evidence_ids: list[str] = Field(min_length=1)
    policy_version: str

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump()


class MerchantRefundRequest(StrictModel):
    request_id: str
    tenant_id: str
    merchant_ref: str
    case_id: str
    transaction_ref: str
    amount_minor: int = Field(ge=1)
    currency: Literal["INR"] = "INR"
    evidence_ids: list[str]
    rationale: str
    status: RequestStatus
    action_id: str | None = None
    approval_id: str | None = None
    case_revision: int | None = Field(default=None, ge=1)
    policy_version: str | None = None
    action_digest: str | None = None
    operation_key: str | None = None
    ledger_status: str | None = None

    @field_validator("amount_minor")
    @classmethod
    def _int_money(cls, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("amount_minor must be an integer number of minor units")
        if value < 1:
            raise ValueError("amount_minor must be positive")
        return value

    def as_wire(self) -> dict[str, Any]:
        """Baseline MerchantRefundRequest fields only."""
        body: dict[str, Any] = {
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
            "merchant_ref": self.merchant_ref,
            "case_id": self.case_id,
            "transaction_ref": self.transaction_ref,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "evidence_ids": list(self.evidence_ids),
            "rationale": self.rationale,
            "status": self.status,
        }
        if self.action_id is not None:
            body["action_id"] = self.action_id
        if self.approval_id is not None:
            body["approval_id"] = self.approval_id
        return body

    def credit_verified(self) -> bool:
        """True only after authoritative credit confirmation via ledger."""
        if self.status != "VERIFIED":
            return False
        return self.ledger_status in CREDIT_VERIFIED_LEDGER_STATUSES


class DraftCreate(StrictModel):
    case_id: str
    transaction_ref: str
    amount_minor: int = Field(ge=1)
    currency: Literal["INR"] = "INR"
    evidence_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class DraftUpdate(StrictModel):
    transaction_ref: str | None = None
    amount_minor: int | None = Field(default=None, ge=1)
    currency: Literal["INR"] | None = None
    evidence_ids: list[str] | None = None
    rationale: str | None = None


class ApprovalDecision(StrictModel):
    decision: Literal["APPROVE", "REJECT"]
    approval_id: str
    action_digest: str
    case_revision: int = Field(ge=1)
    policy_version: str
    expires_at: str
    reviewer_id: str


class CaseRecord(StrictModel):
    contract_version: str = CONTRACT_VERSION
    case_id: str
    revision: int = Field(ge=1)
    status: str
    language: str
    intent: str
    evidence_ids: list[str]
    action_id: str | None = None


class EvidenceRecord(StrictModel):
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
    contract_version: str = CONTRACT_VERSION
    case_id: str
    evidence: list[EvidenceRecord]
    reconciliation_codes: list[str] = Field(default_factory=list)


class PolicyResult(StrictModel):
    outcome: Literal["ALLOW", "REQUIRE_APPROVAL", "DENY", "NEED_EVIDENCE"]
    reason_codes: list[str]
    policy_version: str
    action_digest: str
    required_evidence: list[str] = Field(default_factory=list)


class ActionRecord(StrictModel):
    action_id: str
    provider_ref: str
    payload: dict[str, Any]
    action_digest: str
    status: str
    approval_id: str | None = None


class ProposalRequest(StrictModel):
    operation_key: str
    payload: dict[str, Any]
    action_digest: str


class ReservationRequest(StrictModel):
    operation_key: str
    payload: dict[str, Any]
    action_digest: str
    approval_id: str
