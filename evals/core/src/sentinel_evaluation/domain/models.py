from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

CONTRACT_VERSION = "sentinel.task-contracts.v1"
CONTRACT_SHA256 = "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb"


class SafetyCode(StrEnum):
    UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"
    OVER_REFUND = "OVER_REFUND"
    CROSS_TENANT = "CROSS_TENANT"
    DUPLICATE_EFFECT = "DUPLICATE_EFFECT"
    FALSE_CREDIT = "FALSE_CREDIT"


CRITICAL_SAFETY_CODES: frozenset[SafetyCode] = frozenset(SafetyCode)


@dataclass(frozen=True)
class ExpectedOutcome:
    terminal_state: str
    refund_side_effect_count: int
    refunded_minor: int
    approval_required: bool


@dataclass(frozen=True)
class EvalFixture:
    fixture_id: str
    suite: str
    version: str
    split: str  # development | holdout
    seed: int
    tenant_id: str
    eligible_refund_minor: int
    currency: str
    credit_actually_confirmed: bool
    allowed_actions: tuple[str, ...]
    expected: ExpectedOutcome
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "suite": self.suite,
            "version": self.version,
            "split": self.split,
            "seed": self.seed,
            "tenant_id": self.tenant_id,
            "eligible_refund_minor": self.eligible_refund_minor,
            "currency": self.currency,
            "credit_actually_confirmed": self.credit_actually_confirmed,
            "allowed_actions": list(self.allowed_actions),
            "expected": {
                "terminal_state": self.expected.terminal_state,
                "refund_side_effect_count": self.expected.refund_side_effect_count,
                "refunded_minor": self.expected.refunded_minor,
                "approval_required": self.expected.approval_required,
            },
            "attributes": self.attributes,
        }


@dataclass(frozen=True)
class CandidateObservation:
    """Observed candidate behavior for one fixture. Not authority."""

    terminal_state: str
    refund_side_effect_count: int
    refunded_minor: int
    currency: str
    actions: tuple[str, ...]
    accessed_tenant_id: str
    claims_credit_confirmed: bool
    approval_obtained: bool
    model_mode: str = "fake"

    def to_dict(self) -> dict[str, Any]:
        return {
            "terminal_state": self.terminal_state,
            "refund_side_effect_count": self.refund_side_effect_count,
            "refunded_minor": self.refunded_minor,
            "currency": self.currency,
            "actions": list(self.actions),
            "accessed_tenant_id": self.accessed_tenant_id,
            "claims_credit_confirmed": self.claims_credit_confirmed,
            "approval_obtained": self.approval_obtained,
            "model_mode": self.model_mode,
        }


@dataclass(frozen=True)
class FixtureScore:
    fixture_id: str
    split: str
    outcome_pass: bool
    safety_violations: tuple[SafetyCode, ...]
    safety_pass: bool
    status: str  # PASS | FAIL
    reason_codes: tuple[str, ...]
