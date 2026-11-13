"""Wire-aligned value types (stdlib dataclasses; no framework imports)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

AssessmentStatus = Literal["WAITING", "VERIFIED", "CONFLICT", "ESCALATED"]
RefundStatus = Literal["PENDING", "PROVIDER_CONFIRMED", "FAILED_FINAL"]
ActionState = Literal[
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


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]

    def has_role(self, *roles: str) -> bool:
        return bool(set(self.roles).intersection(roles))

    def allows_case(self, case_id: str) -> bool:
        if not self.case_ids:
            return True
        return case_id in self.case_ids


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    case_id: str
    case_revision: int
    action_id: str
    provider_ref: str

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> VerificationRequest:
        return cls(
            case_id=str(data["case_id"]),
            case_revision=int(data["case_revision"]),
            action_id=str(data["action_id"]),
            provider_ref=str(data["provider_ref"]),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_revision": self.case_revision,
            "action_id": self.action_id,
            "provider_ref": self.provider_ref,
        }


@dataclass(frozen=True, slots=True)
class VerificationResult:
    assessment_id: str
    case_id: str
    case_revision: int
    action_id: str
    assessed_at: str
    expires_at: str
    status: AssessmentStatus
    evidence: tuple[dict[str, Any], ...]
    reason_codes: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
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
class Ack:
    contract_version: str
    job_id: str
    accepted: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "job_id": self.job_id,
            "accepted": True,
        }


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    event_id: str
    tenant_id: str
    merchant_ref: str
    provider_ref: str
    type: Literal["REFUND_STATUS", "CREDIT_STATUS"]
    occurred_at: str


@dataclass(frozen=True, slots=True)
class InboxRecord:
    tenant_id: str
    event_id: str
    provider: str
    provider_ref: str
    event_type: str
    merchant_ref: str
    occurred_at: str
    payload_json: str
    signature_hex: str
    received_at: str
    processed_at: str | None
    process_status: str
    reason_code: str | None
    duplicate: bool = False


@dataclass(frozen=True, slots=True)
class RecheckJob:
    tenant_id: str
    job_id: str
    idempotency_key: str
    case_id: str
    case_revision: int
    action_id: str
    provider_ref: str
    request_digest: str
    available_at: str
    lease_expires_at: str | None
    attempts: int
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ProviderBinding:
    tenant_id: str
    provider_ref: str
    action_id: str
    case_id: str
    case_revision: int
    updated_at: str


@dataclass(frozen=True, slots=True)
class Refund:
    action_id: str
    provider_ref: str
    transaction_ref: str
    amount_minor: int
    currency: str
    status: RefundStatus

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Refund:
        return cls(
            action_id=str(data["action_id"]),
            provider_ref=str(data["provider_ref"]),
            transaction_ref=str(data["transaction_ref"]),
            amount_minor=int(data["amount_minor"]),
            currency=str(data["currency"]),
            status=data["status"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class Credit:
    provider_ref: str
    confirmed: bool
    observed_at: str

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> Credit:
        return cls(
            provider_ref=str(data["provider_ref"]),
            confirmed=bool(data["confirmed"]),
            observed_at=str(data["observed_at"]),
        )


@dataclass(frozen=True, slots=True)
class OutcomeRequest:
    event_key: str
    status: ActionState
    evidence: tuple[dict[str, Any], ...]
    reason_code: str
    lease_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "event_key": self.event_key,
            "status": self.status,
            "evidence": list(self.evidence),
            "reason_code": self.reason_code,
        }
        if self.lease_id is not None:
            body["lease_id"] = self.lease_id
        return body
