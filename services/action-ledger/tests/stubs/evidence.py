"""evidence.v1 stub cases: valid / unavailable / malformed / unauthorized_or_out_of_scope."""

from __future__ import annotations

from collections.abc import Sequence

from sentinel_action_ledger.adapters.network_guard import ReservationNetworkGuard
from sentinel_action_ledger.application.ports import EvidenceItem
from sentinel_action_ledger.domain.errors import (
    ForbiddenError,
    PeerUnavailableError,
    ValidationError,
)
from sentinel_action_ledger.domain.types import Principal

DEMO_PAYMENT = EvidenceItem(
    evidence_id="evidence-payment-b",
    case_id="case-demo-42",
    source="simulator",
    subject_ref="subject-demo-1",
    observed_at="2026-11-13T11:00:00Z",
    expires_at="2026-11-14T12:00:00Z",
    digest="0000000000000000000000000000000000000000000000000000000000000001",
    verification_status="VERIFIED",
    facts={
        "kind": "PAYMENT",
        "payment": {
            "transaction_ref": "TXN-B",
            "order_reference": "DEMO-ORDER-42",
            "subject_ref": "subject-demo-1",
            "status": "CAPTURED",
            "amount_minor": 150000,
            "currency": "INR",
        },
    },
)

DEMO_ORDER = EvidenceItem(
    evidence_id="evidence-order",
    case_id="case-demo-42",
    source="simulator",
    subject_ref="subject-demo-1",
    observed_at="2026-11-13T11:00:00Z",
    expires_at="2026-11-14T12:00:00Z",
    digest="0000000000000000000000000000000000000000000000000000000000000002",
    verification_status="VERIFIED",
    facts={
        "kind": "ORDER",
        "order": {
            "order_reference": "DEMO-ORDER-42",
            "subject_ref": "subject-demo-1",
            "fulfilled_order_count": 1,
            "merchant_confirmed_duplicate": True,
            "paid": True,
        },
    },
)


class EvidenceStub:
    def __init__(
        self,
        case: str = "valid",
        *,
        guard: ReservationNetworkGuard | None = None,
        items: Sequence[EvidenceItem] | None = None,
        amount_minor: int = 150000,
        transaction_ref: str = "TXN-B",
    ) -> None:
        self.case = case
        self.guard = guard
        self.calls = 0
        if items is not None:
            self._items = list(items)
        else:
            payment = EvidenceItem(
                evidence_id=DEMO_PAYMENT.evidence_id,
                case_id=DEMO_PAYMENT.case_id,
                source=DEMO_PAYMENT.source,
                subject_ref=DEMO_PAYMENT.subject_ref,
                observed_at=DEMO_PAYMENT.observed_at,
                expires_at=DEMO_PAYMENT.expires_at,
                digest=DEMO_PAYMENT.digest,
                verification_status=DEMO_PAYMENT.verification_status,
                facts={
                    "kind": "PAYMENT",
                    "payment": {
                        "transaction_ref": transaction_ref,
                        "order_reference": "DEMO-ORDER-42",
                        "subject_ref": "subject-demo-1",
                        "status": "CAPTURED",
                        "amount_minor": amount_minor,
                        "currency": "INR",
                    },
                },
            )
            self._items = [payment, DEMO_ORDER]

    def collect(
        self, *, principal: Principal, case_id: str, case_revision: int, order_reference: str
    ) -> Sequence[EvidenceItem]:
        if self.guard is not None:
            self.guard.note_network()
        self.calls += 1
        if self.case == "unavailable":
            raise PeerUnavailableError("evidence.v1 unavailable")
        if self.case == "malformed":
            raise ValidationError("evidence.v1 malformed", code="PEER_MALFORMED")
        if self.case == "unauthorized_or_out_of_scope":
            raise ForbiddenError("evidence.v1 unauthorized_or_out_of_scope")
        return list(self._items)
