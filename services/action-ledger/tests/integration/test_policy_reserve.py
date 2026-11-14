"""Policy evaluate outcome gates reservation before the TX."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from tests.conftest import auth_header, propose_and_approve, reservation_json

pytestmark = pytest.mark.postgres


def test_policy_deny_blocks_reservation(app_client, tokens):
    proposed, approval = propose_and_approve(app_client, tokens, operation_key="policy-deny")
    app_client.policy.outcome = "DENY"
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json=reservation_json(
            operation_key="policy-deny",
            approval_id=approval["approval_id"],
        ),
    )
    assert reserved.status_code == 409
    assert reserved.json()["code"] == "POLICY_DENIED"
    with app_client.engine.connect() as connection:
        status = connection.execute(
            text("SELECT status FROM actions WHERE action_id = :aid"),
            {"aid": proposed["action_id"]},
        ).scalar_one()
        assert status == "PROPOSED"
        assert connection.execute(text("SELECT count(*) FROM outbox")).scalar_one() == 0
        assert (
            connection.execute(
                text("SELECT count(*) FROM payment_reservations WHERE transaction_ref = 'TXN-B'")
            ).scalar_one()
            == 0
        )


def test_policy_allow_proceeds(app_client, tokens):
    _proposed, approval = propose_and_approve(app_client, tokens, operation_key="policy-allow")
    assert app_client.policy.outcome == "ALLOW"
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json=reservation_json(
            operation_key="policy-allow",
            approval_id=approval["approval_id"],
        ),
    )
    assert reserved.status_code == 201, reserved.text
    assert reserved.json()["status"] == "RESERVED"
    assert app_client.policy.calls >= 1


def test_policy_digest_mismatch_fails(app_client, tokens):
    proposed, approval = propose_and_approve(app_client, tokens, operation_key="policy-digest")
    app_client.policy.action_digest_override = "0" * 64
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json=reservation_json(
            operation_key="policy-digest",
            approval_id=approval["approval_id"],
        ),
    )
    assert reserved.status_code == 409
    assert reserved.json()["code"] == "DIGEST_MISMATCH"
    with app_client.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT status FROM actions WHERE action_id = :aid"),
                {"aid": proposed["action_id"]},
            ).scalar_one()
            == "PROPOSED"
        )


def test_policy_version_mismatch_fails(app_client, tokens):
    proposed, approval = propose_and_approve(app_client, tokens, operation_key="policy-version")
    app_client.policy.policy_version = "other-policy-v9"
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json=reservation_json(
            operation_key="policy-version",
            approval_id=approval["approval_id"],
        ),
    )
    assert reserved.status_code == 409
    assert reserved.json()["code"] == "POLICY_MISMATCH"
    with app_client.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT status FROM actions WHERE action_id = :aid"),
                {"aid": proposed["action_id"]},
            ).scalar_one()
            == "PROPOSED"
        )


def test_missing_order_reference_rejected(app_client, tokens):
    _proposed, approval = propose_and_approve(app_client, tokens, operation_key="no-order-ref")
    body = reservation_json(
        operation_key="no-order-ref",
        approval_id=approval["approval_id"],
    )
    del body["order_reference"]
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json=body,
    )
    assert reserved.status_code == 422
    assert reserved.json()["code"] == "ORDER_REFERENCE_REQUIRED"
