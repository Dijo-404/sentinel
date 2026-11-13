"""In-process case-api.v1 stub for fixture mode."""

from __future__ import annotations

from typing import Any

from ..application.errors import (
    NotFoundError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from ..domain.types import CONTRACT_VERSION, CaseSnapshot, Principal


class StubCaseApi:
    """Fixture peer. Modes mirror tests/stubs cases."""

    def __init__(self, *, mode: str = "valid") -> None:
        if mode not in {
            "valid",
            "unavailable",
            "malformed",
            "unauthorized_or_out_of_scope",
        }:
            raise ValueError(f"unsupported stub mode: {mode}")
        self.mode = mode
        self.cases: dict[str, dict[str, Any]] = {
            "case-demo-42": {
                "contract_version": CONTRACT_VERSION,
                "case_id": "case-demo-42",
                "revision": 1,
                "status": "INVESTIGATING",
                "language": "en-IN",
                "intent": "DUPLICATE_PAYMENT",
                "evidence_ids": ["evidence-payment-b", "evidence-order"],
            }
        }

    def seed(self, case_id: str, **fields: Any) -> None:
        base = {
            "contract_version": CONTRACT_VERSION,
            "case_id": case_id,
            "revision": 1,
            "status": "INVESTIGATING",
            "language": "en-IN",
            "intent": "DUPLICATE_PAYMENT",
            "evidence_ids": [],
        }
        base.update(fields)
        self.cases[case_id] = base

    def get_case(self, case_id: str, *, principal: Principal) -> CaseSnapshot:
        del principal
        if self.mode == "unavailable":
            raise PeerUnavailableError("Required peer unavailable")
        if self.mode == "malformed":
            raise PeerMalformedError("Malformed case-api response")
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerUnauthorizedError("Unauthorized or out of scope")
        body = self.cases.get(case_id)
        if body is None:
            raise NotFoundError("Unknown case")
        return CaseSnapshot(
            case_id=str(body["case_id"]),
            revision=int(body["revision"]),
            status=str(body["status"]),
            contract_version=str(body["contract_version"]),
        )
