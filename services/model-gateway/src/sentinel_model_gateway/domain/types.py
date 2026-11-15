"""Wire types for the workflow proposal and assistant reply contracts. Framework-free."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

Outcome = Literal["PROPOSAL", "NEEDS_INPUT", "ESCALATE"]
ReasonCode = Annotated[str, StringConstraints(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")]


class _Tolerant(BaseModel):
    # Tolerant reader: the workflow caller owns ModelRequest; extra fields must not break us.
    model_config = ConfigDict(extra="ignore")


class CaseRef(_Tolerant):
    case_id: str = Field(min_length=1)


class CaseInput(_Tolerant):
    case_id: str
    case_revision: int = Field(ge=1)
    original_text: str
    language: str
    order_reference: str
    messages: list[dict[str, Any]] = Field(default_factory=list)


class Evidence(_Tolerant):
    evidence_id: str
    source: str = ""
    subject_ref: str = ""
    verification_status: str
    facts: dict[str, Any]


class ModelRequest(_Tolerant):
    """Workflow `ModelRequest` as sent by `HttpModelAdapter` to `POST /v1/proposals`."""

    case: CaseRef
    input: CaseInput
    evidence: list[Evidence]


class ModelResult(BaseModel):
    """Workflow `ModelResult` (strict: the caller validates with extra=forbid)."""

    model_config = ConfigDict(extra="forbid")

    outcome: Outcome
    proposal: dict[str, Any] | None = None
    reason_codes: list[str]
    original_text: str
    language: str


class ProposalDraft(BaseModel):
    """What the LLM may say. Untrusted: grounding decides what reaches the workflow."""

    model_config = ConfigDict(extra="ignore")

    outcome: Outcome
    transaction_ref: str | None = None
    amount_minor: StrictInt | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    reason_codes: list[ReasonCode] = Field(min_length=1, max_length=5)


class ReplyDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str = Field(min_length=1, max_length=4000)
