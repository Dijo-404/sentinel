"""Wire-aligned value objects for merchant-comms.v1 and consumed peers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"
PORT = "merchant-comms.v1"

Language = Literal["en", "ta", "hi"]
DraftStatus = Literal["DRAFT", "APPROVED", "SIMULATED_SENT", "REJECTED"]
LANGUAGES: frozenset[str] = frozenset({"en", "ta", "hi"})


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Principal(StrictModel):
    principal_id: str
    tenant_id: str
    roles: list[str]
    subject_refs: list[str]
    case_ids: list[str]


class WireError(StrictModel):
    code: str
    message: str
    request_id: str


class DeliveryEvent(StrictModel):
    at: str
    channel: str
    status: str


class CommsDraft(StrictModel):
    draft_id: str
    case_id: str
    language: Language
    body: str
    status: DraftStatus
    delivery_history: list[DeliveryEvent] = Field(default_factory=list)


class Case(StrictModel):
    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    case_id: str
    revision: int = Field(ge=1)
    status: str
    language: str
    intent: str
    evidence_ids: list[str]
    action_id: str | None = None


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


class Evidence(StrictModel):
    evidence_id: str
    case_id: str
    source: str
    subject_ref: str
    observed_at: str
    expires_at: str
    digest: str
    verification_status: Literal["VERIFIED", "UNVERIFIED", "CONFLICTING"]
    facts: dict


class ModelRequest(StrictModel):
    case: Case
    input: CaseInput
    evidence: list[Evidence]


class ModelResult(StrictModel):
    outcome: Literal["PROPOSAL", "NEEDS_INPUT", "ESCALATE"]
    proposal: dict | None = None
    reason_codes: list[str]
    original_text: str
    language: str


class DraftCreateRequest(StrictModel):
    case_id: str
    language: Language
    channel: str | None = None


class DraftDecisionRequest(StrictModel):
    decision: Literal["APPROVE", "REJECT"]


class SimulateSendRequest(StrictModel):
    channel: str | None = None


class Capabilities(StrictModel):
    contract_version: Literal["sentinel.task-contracts.v1"] = CONTRACT_VERSION
    component: str = "merchant-comms"
    mode: Literal["fixture", "real-peers"]
