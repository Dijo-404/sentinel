"""Reservation/action/outbox/audit commit or roll back together."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from tests.conftest import auth_header, propose_and_approve
from tests.stubs.evidence import EvidenceStub

from sentinel_action_ledger.domain.digest import action_digest
from sentinel_action_ledger.domain.errors import ConflictError

pytestmark = pytest.mark.postgres


def test_failed_reservation_rolls_back_action_outbox_audit(app_client, tokens):
    """Overrun rejects inside TX: action stays PROPOSED; no outbox; no RESERVED audit."""
    payload = {
        "action": "REQUEST_REFUND",
        "case_id": "case-demo-42",
        "case_revision": 1,
        "transaction_ref": "TXN-B",
        "amount_minor": 150000,
        "currency": "INR",
        "destination": "ORIGINAL_PAYMENT_ROUTE",
        "evidence_ids": ["evidence-payment-b", "evidence-order"],
        "policy_version": "demo-policy-v1",
    }
    digest = action_digest(payload)
    # Eligible capture only 50_000 — reservation of 150_000 must fail closed.
    app_client.evidence._items = EvidenceStub(amount_minor=50000, transaction_ref="TXN-B")._items

    proposed, approval = propose_and_approve(
        app_client, tokens, operation_key="atomic-demo", payload=payload
    )
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "atomic-demo",
            "payload": payload,
            "action_digest": digest,
            "approval_id": approval["approval_id"],
        },
    )
    assert reserved.status_code == 409
    assert reserved.json()["code"] == "INSUFFICIENT_ELIGIBLE"

    with app_client.engine.connect() as connection:
        status = connection.execute(
            text("SELECT status FROM actions WHERE action_id = :aid"),
            {"aid": proposed["action_id"]},
        ).scalar_one()
        assert status == "PROPOSED"
        assert connection.execute(text("SELECT count(*) FROM outbox")).scalar_one() == 0
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM financial_audit "
                    "WHERE action_id = :aid AND event_type = 'RESERVED'"
                ),
                {"aid": proposed["action_id"]},
            ).scalar_one()
            == 0
        )
        # Failed TX must not leave a partial payment row either.
        assert (
            connection.execute(
                text("SELECT count(*) FROM payment_reservations WHERE transaction_ref = 'TXN-B'")
            ).scalar_one()
            == 0
        )


def test_successful_reservation_writes_action_outbox_audit_together(app_client, tokens):
    from tests.conftest import DEMO_DIGEST, DEMO_PAYLOAD

    proposed, approval = propose_and_approve(app_client, tokens, operation_key="atomic-ok")
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "atomic-ok",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
            "approval_id": approval["approval_id"],
        },
    )
    assert reserved.status_code == 201
    action_id = proposed["action_id"]
    with app_client.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT status FROM actions WHERE action_id = :aid"),
                {"aid": action_id},
            ).scalar_one()
            == "RESERVED"
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM outbox WHERE action_id = :aid"),
                {"aid": action_id},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM financial_audit "
                    "WHERE action_id = :aid AND event_type = 'RESERVED'"
                ),
                {"aid": action_id},
            ).scalar_one()
            == 1
        )
        row = connection.execute(
            text("SELECT reserved_minor FROM payment_reservations WHERE transaction_ref = 'TXN-B'")
        ).one()
        assert row.reserved_minor == 150000


def test_network_guard_trips_inside_tx():
    from sentinel_action_ledger.adapters.network_guard import ReservationNetworkGuard

    guard = ReservationNetworkGuard()
    with guard.begin_guard():
        guard.note_network()
        try:
            guard.assert_idle()
            raise AssertionError("expected NETWORK_IN_TX")
        except ConflictError as exc:
            assert exc.code == "NETWORK_IN_TX"
