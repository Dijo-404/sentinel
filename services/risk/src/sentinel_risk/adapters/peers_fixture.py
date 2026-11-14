"""In-process fixture peers. Clearly labeled; never used as real-peer fallback."""

from __future__ import annotations

from typing import Literal

from ..application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from ..domain.types import CONTRACT_VERSION, CaseSnapshot, Principal, ResumeEvent

Behavior = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class FixtureCaseApi:
    def __init__(self, behavior: Behavior = "valid") -> None:
        self.behavior = behavior

    def get_case(self, case_id: str, *, principal: Principal) -> CaseSnapshot:
        del principal
        self._guard("case-api")
        if self.behavior == "malformed":
            raise PeerMalformedError("case-api returned malformed Case")
        return CaseSnapshot(
            contract_version=CONTRACT_VERSION,
            case_id=case_id,
            revision=1,
            status="ESCALATED",
            language="en-IN",
            intent="DUPLICATE_PAYMENT",
            evidence_ids=("evidence-payment-b", "evidence-order"),
            escalation_destination="FRAUD",
        )

    def _guard(self, peer: str) -> None:
        if self.behavior == "unavailable":
            raise PeerUnavailableError(f"Required peer unavailable: {peer}")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerUnauthorizedError(f"{peer} unauthorized or out of scope")


class FixtureWorkflow:
    def __init__(self, behavior: Behavior = "valid") -> None:
        self.behavior = behavior
        self.events: list[ResumeEvent] = []

    def emit_resume(self, event: ResumeEvent, *, principal: Principal) -> None:
        del principal
        self._guard("workflow")
        if event.financial_approval_granted:
            raise PeerMalformedError("workflow reject: financial_approval_granted must be false")
        if self.behavior == "malformed":
            raise PeerMalformedError("workflow rejected malformed resume event")
        self.events.append(event)

    def _guard(self, peer: str) -> None:
        if self.behavior == "unavailable":
            raise PeerUnavailableError(f"Required peer unavailable: {peer}")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerUnauthorizedError(f"{peer} unauthorized or out of scope")
