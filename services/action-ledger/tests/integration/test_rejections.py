"""Approval/lease/provenance rejection matrix."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from tests.conftest import DEMO_DIGEST, DEMO_PAYLOAD, auth_header, propose_and_approve
from tests.stubs.evidence import EvidenceStub
from tests.stubs.policy import PolicyStub

from sentinel_action_ledger.adapters.auth_tokens import TokenPrincipalMap, demo_principals
from sentinel_action_ledger.bootstrap import build_app
from sentinel_action_ledger.domain.types import Principal

pytestmark = pytest.mark.postgres


def test_reject_decision_blocks_reservation(app_client, tokens):
    proposed = app_client.post(
        "/v1/actions/proposals",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "reject-demo",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
        },
    )
    assert proposed.status_code == 201
    action_id = proposed.json()["action_id"]
    decision = app_client.post(
        f"/v1/actions/{action_id}/decisions",
        headers=auth_header(tokens["supervisor"]),
        json={
            "decision": "REJECT",
            "action_digest": DEMO_DIGEST,
            "case_revision": 1,
            "policy_version": "demo-policy-v1",
            "expires_at": "2026-11-13T13:00:00Z",
        },
    )
    assert decision.status_code == 200
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "reject-demo",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
            "approval_id": decision.json()["approval_id"],
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert reserved.status_code == 409
    assert reserved.json()["code"] == "APPROVAL_REJECTED"


def test_lease_mismatch_on_dispatcher_outcome(app_client, tokens):
    _proposed, approval = propose_and_approve(app_client, tokens, operation_key="lease-demo")
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "lease-demo",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
            "approval_id": approval["approval_id"],
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert reserved.status_code == 201
    action_id = reserved.json()["action_id"]
    claimed = app_client.post(
        "/v1/actions/claims",
        headers=auth_header(tokens["dispatcher"]),
        json={"limit": 1},
    )
    assert claimed.status_code == 200
    bad = app_client.post(
        f"/v1/actions/{action_id}/outcomes",
        headers=auth_header(tokens["dispatcher"]),
        json={
            "event_key": "bad-lease",
            "lease_id": "lease-wrong",
            "status": "PENDING",
            "evidence": [],
            "reason_code": "X",
        },
    )
    assert bad.status_code == 409
    assert bad.json()["code"] == "LEASE_MISMATCH"


def test_invalid_transition_rejected(app_client, tokens):
    proposed, approval = propose_and_approve(app_client, tokens, operation_key="trans-demo")
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "trans-demo",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
            "approval_id": approval["approval_id"],
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert reserved.status_code == 201
    action_id = reserved.json()["action_id"]
    bad = app_client.post(
        f"/v1/actions/{action_id}/outcomes",
        headers=auth_header(tokens["verifier"]),
        json={
            "event_key": "skip-states",
            "status": "CREDIT_CONFIRMED",
            "evidence": [],
            "reason_code": "NOPE",
        },
    )
    assert bad.status_code == 409
    assert proposed["action_id"] == action_id


def test_wrong_subject_scope_forbidden(engine, clock, tokens, guard):
    principals = demo_principals()
    wrong = Principal(
        "workflow-wrong-subject",
        "tenant-demo",
        ("workflow",),
        ("subject-other",),
        ("case-demo-42",),
    )
    principals["token-workflow-wrong"] = wrong
    client = TestClient(
        build_app(
            engine=engine,
            evidence=EvidenceStub(guard=guard),
            policy=PolicyStub(guard=guard),
            auth=TokenPrincipalMap(principals),
            clock=clock,
            mode="fixture",
        )
    )
    proposed = client.post(
        "/v1/actions/proposals",
        headers=auth_header("token-workflow-wrong"),
        json={
            "operation_key": "subject-scope-demo",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
        },
    )
    assert proposed.status_code == 201
    action_id = proposed.json()["action_id"]
    decision = client.post(
        f"/v1/actions/{action_id}/decisions",
        headers=auth_header(tokens["supervisor"]),
        json={
            "decision": "APPROVE",
            "action_digest": DEMO_DIGEST,
            "case_revision": 1,
            "policy_version": "demo-policy-v1",
            "expires_at": "2026-11-13T13:00:00Z",
        },
    )
    assert decision.status_code == 200
    reserved = client.post(
        "/v1/actions/reservations",
        headers=auth_header("token-workflow-wrong"),
        json={
            "operation_key": "subject-scope-demo",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
            "approval_id": decision.json()["approval_id"],
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert reserved.status_code == 403


def test_outcome_evidence_mismatch_rejected(app_client, tokens):
    _proposed, approval = propose_and_approve(app_client, tokens, operation_key="ev-mismatch")
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "ev-mismatch",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
            "approval_id": approval["approval_id"],
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert reserved.status_code == 201
    action_id = reserved.json()["action_id"]
    provider_ref = reserved.json()["provider_ref"]
    claimed = app_client.post(
        "/v1/actions/claims",
        headers=auth_header(tokens["dispatcher"]),
        json={"limit": 1},
    )
    lease_id = claimed.json()["commands"][0]["lease_id"]
    pending = app_client.post(
        f"/v1/actions/{action_id}/outcomes",
        headers=auth_header(tokens["dispatcher"]),
        json={
            "event_key": "pending-ev",
            "lease_id": lease_id,
            "status": "PENDING",
            "evidence": [],
            "reason_code": "PROVIDER_ACCEPTED",
        },
    )
    assert pending.status_code == 200
    bad = app_client.post(
        f"/v1/actions/{action_id}/outcomes",
        headers=auth_header(tokens["verifier"]),
        json={
            "event_key": "confirmed-bad-amount",
            "status": "PROVIDER_CONFIRMED",
            "reason_code": "PROVIDER_CONFIRMED",
            "evidence": [
                {
                    "evidence_id": "evidence-refund-bad",
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
                            "action_id": action_id,
                            "provider_ref": provider_ref,
                            "transaction_ref": "TXN-B",
                            "amount_minor": 1,
                            "currency": "INR",
                            "status": "PROVIDER_CONFIRMED",
                        },
                    },
                }
            ],
        },
    )
    assert bad.status_code == 409
    assert bad.json()["code"] == "EVIDENCE_MISMATCH"


def test_pending_outcome_stops_outbox_reclaim(app_client, tokens, clock):
    _proposed, approval = propose_and_approve(app_client, tokens, operation_key="reclaim-demo")
    reserved = app_client.post(
        "/v1/actions/reservations",
        headers=auth_header(tokens["workflow"]),
        json={
            "operation_key": "reclaim-demo",
            "payload": DEMO_PAYLOAD,
            "action_digest": DEMO_DIGEST,
            "approval_id": approval["approval_id"],
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert reserved.status_code == 201
    action_id = reserved.json()["action_id"]
    claimed = app_client.post(
        "/v1/actions/claims",
        headers=auth_header(tokens["dispatcher"]),
        json={"limit": 1},
    )
    assert claimed.status_code == 200
    assert len(claimed.json()["commands"]) == 1
    lease_id = claimed.json()["commands"][0]["lease_id"]
    pending = app_client.post(
        f"/v1/actions/{action_id}/outcomes",
        headers=auth_header(tokens["dispatcher"]),
        json={
            "event_key": "reclaim-pending",
            "lease_id": lease_id,
            "status": "PENDING",
            "evidence": [],
            "reason_code": "PROVIDER_ACCEPTED",
        },
    )
    assert pending.status_code == 200
    # Force expired CLAIMED lease path if outbox were still reclaimable.
    with app_client.engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE outbox SET status = 'CLAIMED', "
                "lease_expires_at = '2026-11-13T11:00:00Z' "
                "WHERE action_id = :aid"
            ),
            {"aid": action_id},
        )
    clock.set(datetime(2026, 11, 13, 12, 10, 0, tzinfo=UTC))
    reclaim = app_client.post(
        "/v1/actions/claims",
        headers=auth_header(tokens["dispatcher"]),
        json={"limit": 10},
    )
    assert reclaim.status_code == 200
    assert reclaim.json()["commands"] == []
    got = app_client.get(
        f"/v1/actions/{action_id}",
        headers=auth_header(tokens["operator"]),
    )
    assert got.status_code == 200
    assert got.json()["status"] == "PENDING"
    with app_client.engine.connect() as connection:
        outbox_status = connection.execute(
            text("SELECT status FROM outbox WHERE action_id = :aid"),
            {"aid": action_id},
        ).scalar_one()
        assert outbox_status == "DONE"
