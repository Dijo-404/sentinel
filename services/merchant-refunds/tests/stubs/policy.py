"""policy.v1 local doubles."""

from __future__ import annotations

from typing import Any, Literal

from sentinel_merchant_refunds.domain.digest import action_digest
from sentinel_merchant_refunds.domain.errors import PeerError, PeerUnavailableError
from sentinel_merchant_refunds.domain.types import PolicyResult, Principal

StubMode = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class StubPolicy:
    def __init__(
        self,
        *,
        mode: StubMode = "valid",
        outcome: Literal["ALLOW", "REQUIRE_APPROVAL", "DENY", "NEED_EVIDENCE"] | None = None,
    ) -> None:
        self.mode = mode
        self.forced_outcome = outcome
        self.calls = 0
        self.last_payload: dict[str, Any] | None = None

    def evaluate(
        self,
        principal: Principal,
        *,
        payload: dict[str, Any],
        evidence_ids: list[str],
        approval: dict[str, Any] | None = None,
    ) -> PolicyResult:
        del principal, evidence_ids
        self.calls += 1
        self.last_payload = dict(payload)
        self._guard()
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed policy response", status_code=502)
        digest = action_digest(payload)
        if self.forced_outcome == "DENY":
            return PolicyResult(
                outcome="DENY",
                reason_codes=["POLICY_DENY"],
                policy_version="demo-policy-v1",
                action_digest=digest,
            )
        if self.forced_outcome == "NEED_EVIDENCE":
            return PolicyResult(
                outcome="NEED_EVIDENCE",
                reason_codes=["NEED_EVIDENCE"],
                policy_version="demo-policy-v1",
                action_digest=digest,
                required_evidence=["evidence-settlement"],
            )
        if approval and approval.get("decision") == "APPROVE":
            if approval.get("action_digest") != digest:
                return PolicyResult(
                    outcome="DENY",
                    reason_codes=["DIGEST_MISMATCH"],
                    policy_version="demo-policy-v1",
                    action_digest=digest,
                )
            return PolicyResult(
                outcome="ALLOW",
                reason_codes=["APPROVED"],
                policy_version="demo-policy-v1",
                action_digest=digest,
            )
        if self.forced_outcome == "ALLOW":
            return PolicyResult(
                outcome="ALLOW",
                reason_codes=["OK"],
                policy_version="demo-policy-v1",
                action_digest=digest,
            )
        return PolicyResult(
            outcome="REQUIRE_APPROVAL",
            reason_codes=["SUPERVISOR_REQUIRED"],
            policy_version="demo-policy-v1",
            action_digest=digest,
        )

    def _guard(self) -> None:
        if self.mode == "unavailable":
            raise PeerUnavailableError("policy")
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
