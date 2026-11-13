"""In-process peer doubles for fixture mode. Negative modes fail closed."""

from __future__ import annotations

from typing import Any, Literal

from sentinel_merchant_inbox.contracts import CONTRACT_VERSION
from sentinel_merchant_inbox.domain.errors import PeerError

StubMode = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class LocalCaseApi:
    def __init__(self, *, mode: StubMode = "valid") -> None:
        self.mode = mode
        self.cases: dict[str, dict[str, Any]] = {}
        self.escalations: list[dict[str, Any]] = []

    def seed(
        self,
        case_id: str,
        *,
        revision: int = 1,
        status: str = "WAITING_EXTERNAL",
    ) -> None:
        self.cases[case_id] = {
            "contract_version": CONTRACT_VERSION,
            "case_id": case_id,
            "revision": revision,
            "status": status,
            "language": "en-IN",
            "intent": "DUPLICATE_PAYMENT",
            "evidence_ids": ["evidence-payment-b", "evidence-order"],
        }

    def get_case(self, case_id: str) -> dict[str, Any]:
        self._guard()
        if case_id not in self.cases:
            raise PeerError("NOT_FOUND", "Unknown case", status_code=404)
        return dict(self.cases[case_id])

    def escalate(
        self,
        case_id: str,
        *,
        expected_revision: int,
        reason_code: str,
        owner_queue: str,
    ) -> dict[str, Any]:
        self._guard()
        if case_id not in self.cases:
            self.seed(case_id)
        current = self.cases[case_id]
        if expected_revision != current["revision"]:
            raise PeerError("CONFLICT", "Stale case revision", status_code=409)
        current = {
            **current,
            "revision": current["revision"] + 1,
            "status": "ESCALATED",
            "reason_code": reason_code,
            "owner_queue": owner_queue,
        }
        self.cases[case_id] = current
        self.escalations.append(
            {
                "case_id": case_id,
                "expected_revision": expected_revision,
                "reason_code": reason_code,
                "owner_queue": owner_queue,
            }
        )
        return dict(current)

    def _guard(self) -> None:
        if self.mode == "unavailable":
            raise PeerError("PEER_UNAVAILABLE", "Required peer unavailable", status_code=503)
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed case-api response", status_code=502)
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)


class LocalEvidence:
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


def default_valid_peers() -> tuple[LocalCaseApi, LocalEvidence]:
    case_api = LocalCaseApi(mode="valid")
    case_api.seed("case-demo-42")
    case_api.seed("case-demo-pending")
    evidence = LocalEvidence(mode="valid")
    evidence.seed("case-demo-42")
    evidence.seed("case-demo-pending")
    return case_api, evidence
