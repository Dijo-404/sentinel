"""evidence.v1 local doubles."""

from __future__ import annotations

from typing import Literal

from sentinel_merchant_refunds import CONTRACT_VERSION
from sentinel_merchant_refunds.domain.errors import PeerError, PeerUnavailableError
from sentinel_merchant_refunds.domain.types import EvidenceBundle, EvidenceRecord, Principal

StubMode = Literal["valid", "unavailable", "malformed", "unauthorized_or_out_of_scope"]


class StubEvidence:
    def __init__(self, *, mode: StubMode = "valid") -> None:
        self.mode = mode
        self.bundles: dict[str, EvidenceBundle] = {}
        self.calls = 0

    def seed_demo(self, case_id: str = "case-demo-42") -> None:
        self.bundles[case_id] = EvidenceBundle(
            contract_version=CONTRACT_VERSION,
            case_id=case_id,
            evidence=[
                EvidenceRecord(
                    evidence_id="evidence-payment-b",
                    case_id=case_id,
                    source="simulator",
                    subject_ref="subject-demo",
                    observed_at="2026-11-13T10:00:00Z",
                    expires_at="2026-11-14T10:00:00Z",
                    digest="b" * 64,
                    verification_status="VERIFIED",
                    facts={
                        "kind": "PAYMENT",
                        "payment": {
                            "transaction_ref": "TXN-B",
                            "status": "CAPTURED",
                            "amount_minor": 150000,
                            "currency": "INR",
                        },
                    },
                ),
                EvidenceRecord(
                    evidence_id="evidence-order",
                    case_id=case_id,
                    source="simulator",
                    subject_ref="subject-demo",
                    observed_at="2026-11-13T10:00:00Z",
                    expires_at="2026-11-14T10:00:00Z",
                    digest="c" * 64,
                    verification_status="VERIFIED",
                    facts={
                        "kind": "ORDER",
                        "order": {
                            "order_reference": "DEMO-ORDER-42",
                            "fulfilled_order_count": 1,
                            "merchant_confirmed_duplicate": True,
                        },
                    },
                ),
            ],
            reconciliation_codes=["DUPLICATE_CAPTURED_PAYMENT"],
        )

    def get_case_evidence(self, principal: Principal, case_id: str) -> EvidenceBundle:
        del principal
        self.calls += 1
        self._guard()
        if self.mode == "malformed":
            raise PeerError("MALFORMED_PEER", "Malformed evidence response", status_code=502)
        if case_id not in self.bundles:
            self.seed_demo(case_id)
        return self.bundles[case_id]

    def _guard(self) -> None:
        if self.mode == "unavailable":
            raise PeerUnavailableError("evidence")
        if self.mode == "unauthorized_or_out_of_scope":
            raise PeerError("FORBIDDEN", "Unauthorized or out of scope", status_code=403)
