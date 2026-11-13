"""evidence.v1 local doubles."""

from __future__ import annotations

from typing import Any, Literal

from sentinel_verifier import CONTRACT_VERSION
from sentinel_verifier.domain.errors import PeerError

StubMode = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class StubEvidence:
    def __init__(self, *, mode: StubMode = "valid") -> None:
        self.mode = mode
        self.bundles: dict[str, dict[str, Any]] = {}

    def seed(self, case_id: str, evidence: list[dict[str, Any]] | None = None) -> None:
        self.bundles[case_id] = {
            "contract_version": CONTRACT_VERSION,
            "case_id": case_id,
            "evidence": evidence or [],
            "reconciliation_codes": [],
        }

    def collect(self, *, case_id: str, case_revision: int, order_reference: str) -> dict[str, Any]:
        del case_revision, order_reference
        self._guard()
        return self.get_case_evidence(case_id)

    def get_case_evidence(self, case_id: str) -> dict[str, Any]:
        self._guard()
        if case_id not in self.bundles:
            self.seed(case_id)
        return dict(self.bundles[case_id])

    def _guard(self) -> None:
        if self.mode == "unavailable":
            raise PeerError("PEER_UNAVAILABLE", "Required peer unavailable", status_code=503)
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed evidence response", status_code=502)
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
