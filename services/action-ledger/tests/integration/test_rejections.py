"""Approval/lease/provenance rejection matrix."""

from __future__ import annotations

import pytest
from tests.conftest import DEMO_DIGEST, DEMO_PAYLOAD, auth_header, propose_and_approve

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
