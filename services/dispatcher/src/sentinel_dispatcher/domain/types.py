"""Wire-aligned domain types for dispatcher.v1."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

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

JobPhase = Literal[
    "CLAIMED",
    "SUBMITTED",
    "RECONCILING",
    "OUTCOME_REPORTED",
    "ESCALATED",
]


@dataclass(frozen=True)
class ProviderCapabilities:
    same_key_retry: bool
    status_lookup: bool


@dataclass(frozen=True)
class Command:
    action_id: str
    provider_ref: str
    payload: Mapping[str, Any]
    action_digest: str
    lease_id: str
    lease_expires_at: str
    provider_capabilities: ProviderCapabilities

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> Command:
        caps = raw["provider_capabilities"]
        return cls(
            action_id=str(raw["action_id"]),
            provider_ref=str(raw["provider_ref"]),
            payload=dict(raw["payload"]),
            action_digest=str(raw["action_digest"]),
            lease_id=str(raw["lease_id"]),
            lease_expires_at=str(raw["lease_expires_at"]),
            provider_capabilities=ProviderCapabilities(
                same_key_retry=bool(caps["same_key_retry"]),
                status_lookup=bool(caps["status_lookup"]),
            ),
        )


@dataclass(frozen=True)
class RefundRequest:
    action_id: str
    provider_ref: str
    transaction_ref: str
    amount_minor: int
    currency: str
    destination: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "provider_ref": self.provider_ref,
            "transaction_ref": self.transaction_ref,
            "amount_minor": self.amount_minor,
            "currency": self.currency,
            "destination": self.destination,
        }

    @classmethod
    def from_command(cls, command: Command) -> RefundRequest:
        payload = command.payload
        return cls(
            action_id=command.action_id,
            provider_ref=command.provider_ref,
            transaction_ref=str(payload["transaction_ref"]),
            amount_minor=int(payload["amount_minor"]),
            currency=str(payload["currency"]),
            destination=str(payload["destination"]),
        )


@dataclass(frozen=True)
class Refund:
    action_id: str
    provider_ref: str
    transaction_ref: str
    amount_minor: int
    currency: str
    status: Literal["PENDING", "PROVIDER_CONFIRMED", "FAILED_FINAL"]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> Refund:
        return cls(
            action_id=str(raw["action_id"]),
            provider_ref=str(raw["provider_ref"]),
            transaction_ref=str(raw["transaction_ref"]),
            amount_minor=int(raw["amount_minor"]),
            currency=str(raw["currency"]),
            status=raw["status"],  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class OutcomeRequest:
    event_key: str
    status: ActionState
    evidence: tuple[Mapping[str, Any], ...]
    reason_code: str
    lease_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "event_key": self.event_key,
            "status": self.status,
            "evidence": [dict(item) for item in self.evidence],
            "reason_code": self.reason_code,
        }
        if self.lease_id is not None:
            body["lease_id"] = self.lease_id
        return body


@dataclass(frozen=True)
class DispatchJob:
    tenant_id: str
    action_id: str
    provider_ref: str
    lease_id: str
    action_digest: str
    payload: Mapping[str, Any]
    phase: JobPhase
    same_key_retry: bool
    status_lookup: bool
    provider_status: str | None = None
    outcome_status: str | None = None
    reason_code: str | None = None


class DomainError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class PeerError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class ProviderTimeout(PeerError):
    """Provider may have accepted the write; outcome is unknown."""

    def __init__(self, message: str = "Provider timeout after possible commit") -> None:
        super().__init__("PROVIDER_TIMEOUT", message, status_code=504)
