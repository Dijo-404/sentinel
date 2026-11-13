"""Command validation before any provider write."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sentinel_dispatcher.domain.digest import action_digest
from sentinel_dispatcher.domain.types import Command, DomainError, RefundRequest


def parse_rfc3339(value: str) -> datetime:
    if not value.endswith("Z"):
        raise DomainError("INVALID_TIMESTAMP", "Timestamps must be UTC RFC3339 with Z")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def validate_command(command: Command, *, now: datetime) -> RefundRequest:
    if not command.action_id or not command.provider_ref or not command.lease_id:
        raise DomainError("INVALID_COMMAND", "action_id, provider_ref, and lease_id are required")
    if not isinstance(command.payload, Mapping):
        raise DomainError("INVALID_COMMAND", "payload must be an object")
    try:
        digest = action_digest(command.payload)
    except ValueError as exc:
        raise DomainError("INVALID_PAYLOAD", str(exc)) from exc
    if digest != command.action_digest:
        raise DomainError("DIGEST_MISMATCH", "Command action_digest does not match payload")
    expires = parse_rfc3339(command.lease_expires_at)
    if expires <= now.astimezone(UTC):
        raise DomainError(
            "LEASE_EXPIRED",
            "Command lease has expired; reservation authority retained",
        )
    request = RefundRequest.from_command(command)
    if request.action_id != command.action_id or request.provider_ref != command.provider_ref:
        raise DomainError("REFERENCE_MISMATCH", "Refund request references must match the command")
    return request


def outcome_event_key(action_id: str, phase: str) -> str:
    return f"dispatcher:{action_id}:{phase}"


def refund_evidence(refund: Mapping[str, Any], *, evidence_id: str, case_id: str) -> dict[str, Any]:
    """Synthetic dispatch-side evidence envelope; verifier owns authoritative confirmation."""
    observed = "2026-11-13T12:00:00Z"
    return {
        "evidence_id": evidence_id,
        "case_id": case_id,
        "source": "dispatcher.v1/simulated-provider",
        "subject_ref": "synthetic-customer",
        "observed_at": observed,
        "expires_at": "2026-11-13T18:00:00Z",
        "digest": "dispatcher-simulated-refund-digest",
        "verification_status": "UNVERIFIED",
        "facts": {"kind": "REFUND", "refund": dict(refund)},
    }
