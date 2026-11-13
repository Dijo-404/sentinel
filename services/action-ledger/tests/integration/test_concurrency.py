"""Real PostgreSQL concurrency: never overrun eligible capture."""

from __future__ import annotations

import concurrent.futures

import pytest
from sqlalchemy import text
from tests.conftest import propose_and_approve
from tests.stubs.evidence import EvidenceStub
from tests.stubs.policy import PolicyStub

from sentinel_action_ledger.adapters.auth_tokens import demo_principals
from sentinel_action_ledger.adapters.ids import SecureIdGenerator
from sentinel_action_ledger.adapters.network_guard import ReservationNetworkGuard
from sentinel_action_ledger.adapters.postgres import PostgresLedgerStore
from sentinel_action_ledger.application.service import ActionLedgerService
from sentinel_action_ledger.domain.digest import action_digest
from sentinel_action_ledger.domain.errors import LedgerError

pytestmark = pytest.mark.postgres


def _payload(amount: int, txn: str = "TXN-CONC") -> dict:
    return {
        "action": "REQUEST_REFUND",
        "case_id": "case-demo-42",
        "case_revision": 1,
        "transaction_ref": txn,
        "amount_minor": amount,
        "currency": "INR",
        "destination": "ORIGINAL_PAYMENT_ROUTE",
        "evidence_ids": ["evidence-payment-b", "evidence-order"],
        "policy_version": "demo-policy-v1",
    }


def test_concurrent_reservations_never_overrun(app_client, tokens, engine, clock):
    """Eight workers each reserve 40000 against 150000 capture → exactly 3 succeed."""
    approvals = []
    for i in range(8):
        payload = _payload(40000)
        _proposed, approval = propose_and_approve(
            app_client,
            tokens,
            operation_key=f"conc-{i}",
            payload=payload,
        )
        approvals.append((f"conc-{i}", payload, action_digest(payload), approval["approval_id"]))

    guard = ReservationNetworkGuard()
    evidence = EvidenceStub(amount_minor=150000, transaction_ref="TXN-CONC", guard=guard)
    policy = PolicyStub(guard=guard)
    service = ActionLedgerService(
        store=PostgresLedgerStore(engine),
        clock=clock,
        ids=SecureIdGenerator(),
        evidence=evidence,
        policy=policy,
        network=guard,
    )
    principal = demo_principals()["token-workflow-demo"]

    def attempt(item):
        operation_key, payload, digest, approval_id = item
        try:
            record, created = service.reserve(
                principal,
                operation_key=operation_key,
                payload=payload,
                digest=digest,
                approval_id=approval_id,
            )
            return "ok", record.status, created
        except LedgerError as exc:
            return "err", exc.code, False

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, approvals))

    successes = [r for r in results if r[0] == "ok"]
    failures = [r for r in results if r[0] == "err"]
    assert len(successes) == 3, results
    assert len(failures) == 5
    assert all(code == "INSUFFICIENT_ELIGIBLE" for _, code, _ in failures)

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT captured_minor, reserved_minor, pending_minor, refunded_minor "
                "FROM payment_reservations WHERE transaction_ref = 'TXN-CONC'"
            )
        ).one()
        assert row.captured_minor == 150000
        assert row.reserved_minor == 120000
        assert row.pending_minor == 0
        assert row.refunded_minor == 0
        assert row.reserved_minor + row.pending_minor + row.refunded_minor <= row.captured_minor
        assert (
            connection.execute(
                text("SELECT count(*) FROM actions WHERE status = 'RESERVED'")
            ).scalar_one()
            == 3
        )
        assert connection.execute(text("SELECT count(*) FROM outbox")).scalar_one() == 3
