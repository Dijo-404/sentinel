"""Payment reservation merchant_ref must come from evidence — never case_id."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.stubs.evidence import DEMO_ORDER, DEMO_PAYMENT, EvidenceStub
from tests.stubs.policy import PolicyStub

from sentinel_action_ledger.adapters.clock import FixedClock
from sentinel_action_ledger.adapters.ids import SecureIdGenerator
from sentinel_action_ledger.adapters.network_guard import ReservationNetworkGuard
from sentinel_action_ledger.application.ports import EvidenceItem
from sentinel_action_ledger.application.service import ActionLedgerService
from sentinel_action_ledger.domain.errors import ConflictError
from sentinel_action_ledger.domain.types import Principal


class _NoopStore:
    """Unused for eligibility-only unit checks."""


def _service(items: list[EvidenceItem]) -> ActionLedgerService:
    return ActionLedgerService(
        store=_NoopStore(),  # type: ignore[arg-type]
        evidence=EvidenceStub(items=items),
        policy=PolicyStub(),
        clock=FixedClock(datetime(2026, 11, 13, 12, 0, 0, tzinfo=UTC)),
        ids=SecureIdGenerator(),
        network=ReservationNetworkGuard(),
    )


_PRINCIPAL = Principal(
    principal_id="workflow",
    tenant_id="tenant-demo",
    roles=("workflow",),
    subject_refs=(),
    case_ids=("*",),
)

_PAYLOAD = {
    "case_id": "case-demo-42",
    "transaction_ref": "TXN-B",
    "currency": "INR",
}


def _payment_without_merchant() -> EvidenceItem:
    return EvidenceItem(
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
                "transaction_ref": "TXN-B",
                "order_reference": "DEMO-ORDER-42",
                "subject_ref": "subject-demo-1",
                "status": "CAPTURED",
                "amount_minor": 150000,
                "currency": "INR",
            },
        },
    )


def test_build_eligibility_requires_payment_merchant_ref() -> None:
    payment = _payment_without_merchant()
    service = _service([payment, DEMO_ORDER])
    with pytest.raises(ConflictError) as exc:
        service._build_eligibility(_PRINCIPAL, _PAYLOAD, [payment, DEMO_ORDER])
    assert exc.value.code == "NEED_MERCHANT_REF"


def test_build_eligibility_rejects_case_id_as_merchant_ref() -> None:
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
                "transaction_ref": "TXN-B",
                "order_reference": "DEMO-ORDER-42",
                "subject_ref": "subject-demo-1",
                "merchant_ref": "case-demo-42",
                "status": "CAPTURED",
                "amount_minor": 150000,
                "currency": "INR",
            },
        },
    )
    service = _service([payment, DEMO_ORDER])
    with pytest.raises(ConflictError) as exc:
        service._build_eligibility(_PRINCIPAL, _PAYLOAD, [payment, DEMO_ORDER])
    assert exc.value.code == "INVALID_MERCHANT_REF"


def test_build_eligibility_keeps_evidence_merchant_ref() -> None:
    service = _service([DEMO_PAYMENT, DEMO_ORDER])
    snapshot = service._build_eligibility(_PRINCIPAL, _PAYLOAD, [DEMO_PAYMENT, DEMO_ORDER])
    assert snapshot.merchant_ref == "merchant-demo-1"
    assert snapshot.merchant_ref != snapshot.case_id
