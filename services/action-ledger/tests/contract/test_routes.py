"""HTTP contract routes against real Postgres + local stubs."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from tests.conftest import DEMO_DIGEST, DEMO_PAYLOAD, auth_header, propose_and_approve

pytestmark = pytest.mark.postgres


def test_happy_path_propose_decide_reserve_claim_outcome(app_client, tokens):
    proposed, approval = propose_and_approve(app_client, tokens)
    assert proposed["status"] == "PROPOSED"
    assert "provider_ref" in proposed
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "duplicate-demo-42-b",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
            "approval_id": approval["approval_id"],
        },
    )
    assert reserved.status_code == 201, reserved.text
    body = reserved.json()
    assert body["status"] == "RESERVED"
    assert body["action_id"] == proposed["action_id"]
    assert body["provider_ref"] == proposed["provider_ref"]

    retry = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "duplicate-demo-42-b",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
            "approval_id": approval["approval_id"],
        },
    )
    assert retry.status_code == 200
    assert retry.json() == body

    claimed = app_client.post(
        "/v1/actions/claims",
        headers=auth_header(tokens["dispatcher"]),
        json={"limit": 1},
    )
    assert claimed.status_code == 200
    commands = claimed.json()["commands"]
    assert len(commands) == 1
    assert commands[0]["action_id"] == body["action_id"]
    assert commands[0]["provider_ref"] == body["provider_ref"]
    lease_id = commands[0]["lease_id"]

    pending = app_client.post(
        f"/v1/actions/{body['action_id']}/outcomes",
        headers=auth_header(tokens["dispatcher"]),
        json={
            "event_key": "outcome-pending-1",
            "lease_id": lease_id,
            "status": "PENDING",
            "evidence": [],
            "reason_code": "PROVIDER_ACCEPTED",
        },
    )
    assert pending.status_code == 200
    assert pending.json()["status"] == "PENDING"

    confirmed = app_client.post(
        f"/v1/actions/{body['action_id']}/outcomes",
        headers=auth_header(tokens["verifier"]),
        json={
            "event_key": "outcome-confirmed-1",
            "status": "PROVIDER_CONFIRMED",
            "reason_code": "PROVIDER_CONFIRMED",
            "evidence": [
                {
                    "evidence_id": "evidence-refund-1",
                    "case_id": "case-demo-42",
                    "source": "verifier",
                    "subject_ref": "subject-demo-1",
                    "observed_at": "2026-11-13T12:01:00Z",
                    "expires_at": "2026-11-14T12:00:00Z",
                    "digest": "abc",
                    "verification_status": "VERIFIED",
                    "facts": {
                        "kind": "REFUND",
                        "refund": {
                            "action_id": body["action_id"],
                            "provider_ref": body["provider_ref"],
                            "transaction_ref": "TXN-B",
                            "amount_minor": 150000,
                            "currency": "INR",
                            "status": "PROVIDER_CONFIRMED",
                        },
                    },
                }
            ],
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "PROVIDER_CONFIRMED"

    with app_client.engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT reserved_minor, pending_minor, refunded_minor "
                "FROM payment_reservations WHERE transaction_ref = 'TXN-B'"
            )
        ).one()
        assert row.reserved_minor == 0
        assert row.pending_minor == 0
        assert row.refunded_minor == 150000
        audits = connection.execute(text("SELECT count(*) FROM financial_audit")).scalar_one()
        assert audits >= 4


def test_operation_key_conflict(app_client, tokens):
    propose_and_approve(app_client, tokens)
    other = {**DEMO_PAYLOAD, "amount_minor": 100000}
    from sentinel_action_ledger.domain.digest import action_digest

    conflict = app_client.post(
        "/v1/actions/proposals",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "duplicate-demo-42-b",
            "payload": other,
            "action_digest": action_digest(other),
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_expired_approval_rejected(app_client, tokens, clock):
    proposed, approval = propose_and_approve(app_client, tokens)
    from datetime import UTC, datetime

    clock.set(datetime(2026, 11, 13, 14, 0, 0, tzinfo=UTC))
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "duplicate-demo-42-b",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
            "approval_id": approval["approval_id"],
        },
    )
    assert reserved.status_code == 409
    assert reserved.json()["code"] == "APPROVAL_EXPIRED"
    assert proposed["action_id"]


def test_role_rejection_and_digest_mismatch(app_client, tokens):
    bad_role = app_client.post(
        "/v1/actions/proposals",
        headers=auth_header(tokens["dispatcher"]),
        json={
            "operation_key": "x",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
        },
    )
    assert bad_role.status_code == 403

    mismatch = app_client.post(
        "/v1/actions/proposals",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "y",
            "payload": DEMO_PAYLOAD,
            "action_digest": "0" * 64,
        },
    )
    assert mismatch.status_code == 422


def test_peer_stub_cases(engine, clock, tokens, guard):
    from fastapi.testclient import TestClient
    from tests.stubs.evidence import EvidenceStub
    from tests.stubs.policy import PolicyStub

    from sentinel_action_ledger.adapters.auth_tokens import TokenPrincipalMap, demo_principals
    from sentinel_action_ledger.bootstrap import build_app

    for case in ("unavailable", "malformed", "unauthorized_or_out_of_scope"):
        with engine.begin() as connection:
            for table in (
                "outcome_events",
                "financial_audit",
                "outbox",
                "eligibility_snapshots",
                "payment_reservations",
                "approvals",
                "actions",
            ):
                connection.execute(text(f"TRUNCATE {table} CASCADE"))
        evidence = EvidenceStub(case=case, guard=guard)
        policy = PolicyStub(guard=guard)
        client = TestClient(
            build_app(
                engine=engine,
                evidence=evidence,
                policy=policy,
                auth=TokenPrincipalMap(demo_principals()),
                clock=clock,
                mode="fixture",
            )
        )
        proposed, approval = propose_and_approve(client, tokens, operation_key=f"op-{case}")
        reserved = client.post(
            "/v1/actions/reservations",
            headers=auth_header(tokens["workflow"]),
            json={
                "operation_key": f"op-{case}",
                "payload": DEMO_PAYLOAD,
                "action_digest": DEMO_DIGEST,
                "approval_id": approval["approval_id"],
            },
        )
        assert reserved.status_code in {403, 422, 503}, (case, reserved.text)
        assert proposed["status"] == "PROPOSED"


def test_capabilities_and_health(app_client):
    assert app_client.get("/healthz").json()["status"] == "ok"
    assert app_client.get("/readyz").json()["status"] == "fixture-ready"
    caps = app_client.get("/v1/capabilities").json()
    assert caps["component"] == "action-ledger"
    assert caps["contract_version"] == "sentinel.task-contracts.v1"
    assert caps["mode"] == "fixture"
