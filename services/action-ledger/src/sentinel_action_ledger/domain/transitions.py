"""Provenance-bound action state transitions."""

from __future__ import annotations

from .errors import ConflictError, ForbiddenError, ValidationError
from .types import ActionState

# (from_status, to_status) -> required role provenance
_ALLOWED: dict[tuple[str, str], frozenset[str]] = {
    ("RESERVED", "DISPATCHING"): frozenset({"dispatcher"}),
    ("DISPATCHING", "PENDING"): frozenset({"dispatcher"}),
    ("DISPATCHING", "OUTCOME_UNKNOWN"): frozenset({"dispatcher"}),
    ("DISPATCHING", "ESCALATED"): frozenset({"dispatcher", "verifier"}),
    ("PENDING", "PROVIDER_CONFIRMED"): frozenset({"verifier"}),
    ("PENDING", "FAILED_FINAL"): frozenset({"verifier"}),
    ("PENDING", "ESCALATED"): frozenset({"dispatcher", "verifier"}),
    ("OUTCOME_UNKNOWN", "PENDING"): frozenset({"dispatcher"}),
    ("OUTCOME_UNKNOWN", "PROVIDER_CONFIRMED"): frozenset({"verifier"}),
    ("OUTCOME_UNKNOWN", "FAILED_FINAL"): frozenset({"verifier"}),
    ("OUTCOME_UNKNOWN", "ESCALATED"): frozenset({"dispatcher", "verifier"}),
    ("PROVIDER_CONFIRMED", "CREDIT_CONFIRMED"): frozenset({"verifier"}),
    ("PROVIDER_CONFIRMED", "ESCALATED"): frozenset({"verifier"}),
    ("ESCALATED", "PENDING"): frozenset({"dispatcher"}),
    ("ESCALATED", "PROVIDER_CONFIRMED"): frozenset({"verifier"}),
    ("ESCALATED", "FAILED_FINAL"): frozenset({"verifier"}),
    ("ESCALATED", "CREDIT_CONFIRMED"): frozenset({"verifier"}),
    ("ESCALATED", "OUTCOME_UNKNOWN"): frozenset({"dispatcher"}),
}

_TERMINAL = frozenset({"CREDIT_CONFIRMED", "FAILED_FINAL"})


def assert_transition(
    current: ActionState,
    target: ActionState,
    *,
    roles: tuple[str, ...],
) -> None:
    if current == target:
        return
    if current in _TERMINAL:
        raise ConflictError("Terminal action cannot transition", code="INVALID_TRANSITION")
    allowed_roles = _ALLOWED.get((current, target))
    if allowed_roles is None:
        raise ConflictError(
            f"Invalid transition {current} -> {target}",
            code="INVALID_TRANSITION",
        )
    if not allowed_roles.intersection(roles):
        raise ForbiddenError("Role cannot apply this outcome transition")


def require_evidence_kinds(target: ActionState) -> frozenset[str]:
    if target in {"PROVIDER_CONFIRMED", "FAILED_FINAL"}:
        return frozenset({"REFUND"})
    if target == "CREDIT_CONFIRMED":
        return frozenset({"CREDIT"})
    return frozenset()


def validate_outcome_status(status: str) -> ActionState:
    allowed = {
        "PENDING",
        "OUTCOME_UNKNOWN",
        "PROVIDER_CONFIRMED",
        "CREDIT_CONFIRMED",
        "FAILED_FINAL",
        "ESCALATED",
        "DISPATCHING",
    }
    if status not in allowed:
        raise ValidationError(f"Unsupported outcome status {status}")
    return status  # type: ignore[return-value]
