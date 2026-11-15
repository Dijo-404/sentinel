"""policy.v1 stub cases: valid / unavailable / malformed / unauthorized_or_out_of_scope."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sentinel_action_ledger.adapters.network_guard import ReservationNetworkGuard
from sentinel_action_ledger.application.ports import EvidenceItem
from sentinel_action_ledger.domain.digest import action_digest
from sentinel_action_ledger.domain.errors import (
    ForbiddenError,
    PeerUnavailableError,
    ValidationError,
)
from sentinel_action_ledger.domain.types import Approval, Principal


class PolicyStub:
    def __init__(
        self,
        case: str = "valid",
        *,
        guard: ReservationNetworkGuard | None = None,
        policy_version: str = "demo-policy-v1",
        outcome: str = "ALLOW",
        action_digest_override: str | None = None,
        require_approval: bool = False,
    ) -> None:
        self.case = case
        self.guard = guard
        self.policy_version = policy_version
        self.outcome = outcome
        self.action_digest_override = action_digest_override
        # Mirrors real policy.v1: a refund without an APPROVE approval -> REQUIRE_APPROVAL.
        self.require_approval = require_approval
        self.last_approval: Approval | None = None
        self.calls = 0

    def evaluate(
        self,
        *,
        principal: Principal,
        payload: dict[str, Any],
        evidence: Sequence[EvidenceItem],
        approval: Approval | None = None,
    ) -> dict[str, Any]:
        if self.guard is not None:
            self.guard.note_network()
        self.calls += 1
        self.last_approval = approval
        if self.case == "unavailable":
            raise PeerUnavailableError("policy.v1 unavailable")
        if self.case == "malformed":
            raise ValidationError("policy.v1 malformed", code="PEER_MALFORMED")
        if self.case == "unauthorized_or_out_of_scope":
            raise ForbiddenError("policy.v1 unauthorized_or_out_of_scope")
        digest = (
            self.action_digest_override
            if self.action_digest_override is not None
            else action_digest(payload)
        )
        outcome = self.outcome
        if self.require_approval and (approval is None or approval.decision != "APPROVE"):
            outcome = "REQUIRE_APPROVAL"
        return {
            "outcome": outcome,
            "reason_codes": [] if outcome == "ALLOW" else ["POLICY_BLOCK"],
            "policy_version": self.policy_version,
            "action_digest": digest,
            "required_evidence": [],
        }
