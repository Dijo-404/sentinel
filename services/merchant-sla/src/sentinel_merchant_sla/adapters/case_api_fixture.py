"""In-process case-api.v1 fixture peer. Labeled fixture mode only."""

from __future__ import annotations

from typing import Literal

from sentinel_merchant_sla.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_sla.contracts import CaseRecord, Principal, parse_case

Behavior = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class FixtureCaseApi:
    """Deterministic local double for case-api.v1."""

    def __init__(
        self,
        behavior: Behavior = "valid",
        *,
        case: CaseRecord | None = None,
    ) -> None:
        self.behavior = behavior
        self._case = case or CaseRecord(
            case_id="case-demo-42",
            revision=1,
            status="INVESTIGATING",
            language="en-IN",
            intent="DUPLICATE_PAYMENT",
            evidence_ids=("evidence-payment-a",),
            contract_version="sentinel.task-contracts.v1",
            tenant_id="demo-tenant-a",
            merchant_ref="merchant-demo-a",
            opened_at="2026-11-13T10:00:00Z",
        )

    def get_case(self, case_id: str, principal: Principal) -> CaseRecord:
        del principal
        self._guard()
        if self.behavior == "malformed":
            raise PeerMalformedError("malformed case")
        return self._resolve(case_id)

    def escalate_case(
        self,
        case_id: str,
        *,
        expected_revision: int,
        reason_code: str,
        owner_queue: str,
        principal: Principal,
    ) -> CaseRecord:
        del reason_code, owner_queue, principal
        self._guard()
        if self.behavior == "malformed":
            raise PeerMalformedError("malformed escalate response")
        current = self._resolve(case_id)
        if expected_revision != current.revision:
            raise PeerMalformedError("revision conflict on escalate")
        # Escalation is a handoff — never VERIFIED_RESOLVED.
        self._case = CaseRecord(
            case_id=current.case_id,
            revision=current.revision + 1,
            status="ESCALATED",
            language=current.language,
            intent=current.intent,
            evidence_ids=current.evidence_ids,
            contract_version=current.contract_version,
            tenant_id=current.tenant_id,
            merchant_ref=current.merchant_ref,
            opened_at=current.opened_at,
        )
        return self._case

    def _resolve(self, case_id: str) -> CaseRecord:
        if case_id == self._case.case_id:
            return self._case
        return CaseRecord(
            case_id=case_id,
            revision=1,
            status="RECEIVED",
            language="en-IN",
            intent="UNKNOWN",
            evidence_ids=(),
            contract_version="sentinel.task-contracts.v1",
            tenant_id=self._case.tenant_id,
            merchant_ref=self._case.merchant_ref,
            opened_at=self._case.opened_at,
        )

    def _guard(self) -> None:
        if self.behavior == "unavailable":
            raise PeerUnavailableError("case-api")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerUnauthorizedError("out of scope")


def case_from_fixture_dict(raw: dict) -> CaseRecord:
    return parse_case(raw)
