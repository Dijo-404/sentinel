"""Wire-aligned value types (stdlib dataclasses; no framework imports)."""

from __future__ import annotations

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

Decision = Literal["APPROVE", "REJECT"]

ALLOCATING_STATES: frozenset[str] = frozenset(
    {
        "RESERVED",
        "DISPATCHING",
        "OUTCOME_UNKNOWN",
        "PENDING",
        "PROVIDER_CONFIRMED",
        "CREDIT_CONFIRMED",
        "ESCALATED",
    }
)

PENDING_BALANCE_STATES: frozenset[str] = frozenset({"PENDING"})
COMPLETED_BALANCE_STATES: frozenset[str] = frozenset({"PROVIDER_CONFIRMED", "CREDIT_CONFIRMED"})
RESERVED_BALANCE_STATES: frozenset[str] = frozenset(
    {"RESERVED", "DISPATCHING", "OUTCOME_UNKNOWN", "ESCALATED"}
)


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    subject_refs: tuple[str, ...]
    case_ids: tuple[str, ...]

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def allows_case(self, case_id: str) -> bool:
        if not self.case_ids:
            return True
        return case_id in self.case_ids


@dataclass(frozen=True, slots=True)
class Approval:
    approval_id: str
    action_digest: str
    case_revision: int
    policy_version: str
    decision: Decision
    reviewer_id: str
    expires_at: str


@dataclass(frozen=True, slots=True)
class ActionRecord:
    action_id: str
    provider_ref: str
    payload: dict[str, Any]
    action_digest: str
    status: ActionState
    approval: Approval | None = None


@dataclass(frozen=True, slots=True)
class Command:
    action_id: str
    provider_ref: str
    payload: dict[str, Any]
    action_digest: str
    lease_id: str
    lease_expires_at: str
    provider_capabilities: dict[str, bool]


@dataclass(frozen=True, slots=True)
class ClaimResult:
    commands: tuple[Command, ...]


@dataclass(frozen=True, slots=True)
class EligibilitySnapshot:
    tenant_id: str
    transaction_ref: str
    case_id: str
    subject_ref: str
    captured_minor: int
    currency: str
    payment_status: str
    observed_at: str
    expires_at: str
    evidence_digest: str
    external_refunded_minor: int
    external_pending_minor: int
    version: int
