"""In-process fixture peers. Clearly labeled; never used as real-peer fallback."""

from __future__ import annotations

from typing import Literal

from ..application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from ..domain.types import (
    CONTRACT_VERSION,
    CaseSnapshot,
    EvidenceBundle,
    EvidenceItem,
    Principal,
)

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
            status="INVESTIGATING",
            language="en-IN",
            intent="DUPLICATE_PAYMENT",
            evidence_ids=("evidence-payment-b", "evidence-order"),
            order_reference="DEMO-ORDER-42",
        )

    def _guard(self, peer: str) -> None:
        if self.behavior == "unavailable":
            raise PeerUnavailableError(f"Required peer unavailable: {peer}")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerUnauthorizedError(f"{peer} unauthorized or out of scope")


class FixtureEvidence:
    def __init__(
        self,
        behavior: Behavior = "valid",
        *,
        incomplete: bool = False,
    ) -> None:
        self.behavior = behavior
        self.incomplete = incomplete

    def collect(
        self,
        *,
        case_id: str,
        case_revision: int,
        order_reference: str,
        principal: Principal,
    ) -> EvidenceBundle:
        del case_revision, order_reference, principal
        self._guard("evidence")
        if self.behavior == "malformed":
            raise PeerMalformedError("evidence returned malformed EvidenceBundle")
        items = [
            _item(
                "evidence-payment-b",
                case_id,
                {
                    "kind": "PAYMENT",
                    "payment": {
                        "transaction_ref": "TXN-B",
                        "order_reference": "DEMO-ORDER-42",
                        "subject_ref": "subj-demo-1",
                        "status": "CAPTURED",
                        "amount_minor": 150000,
                        "currency": "INR",
                    },
                },
            ),
            _item(
                "evidence-order",
                case_id,
                {
                    "kind": "ORDER",
                    "order": {
                        "order_reference": "DEMO-ORDER-42",
                        "subject_ref": "subj-demo-1",
                        "fulfilled_order_count": 1,
                        "merchant_confirmed_duplicate": True,
                        "paid": True,
                    },
                },
            ),
        ]
        if not self.incomplete:
            items.append(
                _item(
                    "evidence-delivery",
                    case_id,
                    {
                        "kind": "DELIVERY",
                        "delivery": {
                            "order_reference": "DEMO-ORDER-42",
                            "delivered": True,
                            "carrier_ref": "DELIVERY-DEMO-1",
                        },
                    },
                )
            )
        return EvidenceBundle(
            contract_version=CONTRACT_VERSION,
            case_id=case_id,
            evidence=tuple(items),
            reconciliation_codes=("FIXTURE_PACKET",),
        )

    def _guard(self, peer: str) -> None:
        if self.behavior == "unavailable":
            raise PeerUnavailableError(f"Required peer unavailable: {peer}")
        if self.behavior == "unauthorized_or_out_of_scope":
            raise PeerUnauthorizedError(f"{peer} unauthorized or out of scope")


def _item(evidence_id: str, case_id: str, facts: dict) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        case_id=case_id,
        source="fixture",
        subject_ref="subj-demo-1",
        observed_at="2026-11-13T12:00:00Z",
        expires_at="2026-11-13T18:00:00Z",
        digest="a" * 64,
        verification_status="VERIFIED",
        facts=facts,
    )
