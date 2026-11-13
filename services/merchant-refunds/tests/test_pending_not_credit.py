"""PENDING / PROVIDER_CONFIRMED never count as verified customer credit."""

from __future__ import annotations

import pytest
from tests.stubs import StubCaseApi, StubEvidence, StubLedger, StubPolicy

from sentinel_merchant_refunds.adapters.clock import FixedClock
from sentinel_merchant_refunds.adapters.ids import SecureIdGenerator
from sentinel_merchant_refunds.adapters.memory_store import MemoryRequestStore
from sentinel_merchant_refunds.application.service import MerchantRefundService
from sentinel_merchant_refunds.domain.status import is_customer_credit, map_ledger_status
from sentinel_merchant_refunds.domain.types import ApprovalDecision, DraftCreate, Principal


def _svc(ledger: StubLedger) -> MerchantRefundService:
    evidence = StubEvidence()
    evidence.seed_demo()
    return MerchantRefundService(
        store=MemoryRequestStore(),
        case_api=StubCaseApi(),
        evidence=evidence,
        policy=StubPolicy(),
        ledger=ledger,
        clock=FixedClock("2026-11-13T12:00:00Z"),
        ids=SecureIdGenerator(),
    )


def _principal() -> Principal:
    return Principal(
        principal_id="staff-demo-1",
        tenant_id="tenant-demo-1",
        merchant_ref="merchant-demo-1",
        roles=["merchant_staff"],
    )


def _reach_reserved(svc: MerchantRefundService, ledger: StubLedger):
    principal = _principal()
    draft = svc.create_draft(
        principal,
        DraftCreate(
            case_id="case-demo-42",
            transaction_ref="TXN-B",
            amount_minor=150000,
            evidence_ids=["evidence-payment-b", "evidence-order"],
            rationale="dup",
        ),
        idempotency_key="pending-credit-1",
    )
    awaiting = svc.submit(principal, draft.request_id)
    reserved = svc.apply_decision(
        principal,
        draft.request_id,
        ApprovalDecision(
            decision="APPROVE",
            approval_id="approval-demo-1",
            action_digest=awaiting.action_digest or "",
            case_revision=1,
            policy_version="demo-policy-v1",
            expires_at="2026-11-13T18:00:00Z",
            reviewer_id="supervisor-demo-1",
        ),
    )
    assert reserved.status == "RESERVED"
    assert reserved.credit_verified() is False
    return principal, reserved


@pytest.mark.parametrize(
    "ledger_status,expected_request_status,credit",
    [
        ("PENDING", "RESERVED", False),
        ("PROVIDER_CONFIRMED", "RESERVED", False),
        ("DISPATCHING", "RESERVED", False),
        ("OUTCOME_UNKNOWN", "RESERVED", False),
        ("CREDIT_CONFIRMED", "VERIFIED", True),
        ("FAILED_FINAL", "FAILED", False),
    ],
)
def test_sync_maps_ledger_status(ledger_status, expected_request_status, credit):
    ledger = StubLedger()
    svc = _svc(ledger)
    principal, reserved = _reach_reserved(svc, ledger)
    ledger.set_status(reserved.action_id or "", ledger_status)
    synced = svc.sync(principal, reserved.request_id)
    assert synced.status == expected_request_status
    assert synced.ledger_status == ledger_status
    assert synced.credit_verified() is credit
    assert is_customer_credit(synced.ledger_status, synced.status) is credit


def test_map_pending_is_not_verified():
    assert map_ledger_status("PENDING") == "RESERVED"
    assert map_ledger_status("PROVIDER_CONFIRMED") == "RESERVED"
    assert map_ledger_status("CREDIT_CONFIRMED") == "VERIFIED"
