"""case-api.v1 local doubles."""

from __future__ import annotations

from typing import Any, Literal

from sentinel_verifier import CONTRACT_VERSION
from sentinel_verifier.domain.errors import PeerError

StubMode = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class StubCaseApi:
    def __init__(self, *, mode: StubMode = "valid") -> None:
        self.mode = mode
        self.cases: dict[str, dict[str, Any]] = {}
        self.results: list[dict[str, Any]] = []

    def seed(self, case_id: str, *, revision: int = 1, status: str = "WAITING_EXTERNAL") -> None:
        self.cases[case_id] = {
            "contract_version": CONTRACT_VERSION,
            "case_id": case_id,
            "revision": revision,
            "status": status,
            "language": "en-IN",
            "intent": "DUPLICATE_PAYMENT",
            "evidence_ids": ["evidence-payment-b", "evidence-order"],
            "action_id": "action-demo-1",
        }

    def get_case(self, case_id: str) -> dict[str, Any]:
        self._guard()
        if case_id not in self.cases:
            raise PeerError("NOT_FOUND", "Unknown case", status_code=404)
        return dict(self.cases[case_id])

    def submit_result(self, case_id: str, result: dict[str, Any]) -> dict[str, Any]:
        self._guard()
        if case_id not in self.cases:
            self.seed(case_id)
        current = self.cases[case_id]
        if result.get("expected_revision") != current["revision"]:
            raise PeerError("CONFLICT", "Stale case revision", status_code=409)
        current = {
            **current,
            "revision": current["revision"] + 1,
            "status": result["status"],
            "action_id": result.get("action_id"),
            "assessment_id": result.get("assessment_id"),
        }
        self.cases[case_id] = current
        self.results.append({"case_id": case_id, **result})
        return dict(current)

    def _guard(self) -> None:
        if self.mode == "unavailable":
            raise PeerError("PEER_UNAVAILABLE", "Required peer unavailable", status_code=503)
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed case-api response", status_code=502)
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
