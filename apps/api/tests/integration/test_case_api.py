"""Acceptance: intake, idempotency, authz, events, decisions, results."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine

from sentinel_api.adapters.peers.fixture_clients import sample_verified_assessment
from tests.conftest import auth

CREATE = {
    "message": "I was charged twice for DEMO-ORDER-42",
    "language": "en-IN",
    "order_reference": "DEMO-ORDER-42",
    "channel": "web",
}


def _create(client, token="token-customer-a", key="idem-1", body=None):
    return client.post(
        "/v1/cases",
        headers={**auth(token), "Idempotency-Key": key},
        json=body or CREATE,
    )


def test_health_and_capabilities(client):
    assert client.get("/healthz").status_code == 200
    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps["component"] == "case-api"
    assert caps["mode"] == "fixture"


def test_create_returns_202_and_reuses_idempotency_key(client, app):
    first = _create(client)
    assert first.status_code == 202
    body = first.json()
    assert body["status"] == "RECEIVED"
    assert body["status_url"].startswith("/v1/cases/")
    case_id = body["case_id"]

    second = _create(client)
    assert second.status_code == 202
    assert second.json()["case_id"] == case_id

    conflict = _create(
        client,
        key="idem-1",
        body={**CREATE, "message": "different payload"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"

    # Workflow START scheduled for first create.
    assert any(c.event == "START" for c in app.state.peers["workflow"].calls)


def test_role_and_tenant_boundaries(client):
    created = _create(client).json()
    case_id = created["case_id"]

    ok = client.get(f"/v1/cases/{case_id}", headers=auth("token-customer-a"))
    assert ok.status_code == 200

    other_customer = client.get(f"/v1/cases/{case_id}", headers=auth("token-customer-b"))
    assert other_customer.status_code == 404

    other_tenant = client.get(f"/v1/cases/{case_id}", headers=auth("token-customer-other-tenant"))
    assert other_tenant.status_code == 404

    operator = client.get(f"/v1/cases/{case_id}", headers=auth("token-operator"))
    assert operator.status_code == 200

    customer_ops = client.get("/v1/ops/cases", headers=auth("token-customer-a"))
    assert customer_ops.status_code == 403


def test_messages_revision_and_immutable_input(client):
    case_id = _create(client).json()["case_id"]
    msg = client.post(
        f"/v1/cases/{case_id}/messages",
        headers=auth("token-customer-a"),
        json={"message": "Still waiting", "language": "en-IN", "expected_revision": 1},
    )
    assert msg.status_code == 202
    assert msg.json()["revision"] == 2

    stale = client.post(
        f"/v1/cases/{case_id}/messages",
        headers=auth("token-customer-a"),
        json={"message": "stale", "language": "en-IN", "expected_revision": 1},
    )
    assert stale.status_code == 409

    snap1 = client.get(
        f"/v1/internal/cases/{case_id}/input?revision=1",
        headers=auth("token-workflow"),
    )
    assert snap1.status_code == 200
    assert snap1.json()["case_revision"] == 1
    assert len(snap1.json()["messages"]) == 1

    snap2 = client.get(
        f"/v1/internal/cases/{case_id}/input?revision=2",
        headers=auth("token-workflow"),
    )
    assert snap2.status_code == 200
    assert len(snap2.json()["messages"]) == 2
    assert snap2.json()["original_text"] == CREATE["message"]

    missing = client.get(
        f"/v1/internal/cases/{case_id}/input?revision=99",
        headers=auth("token-workflow"),
    )
    assert missing.status_code == 404


def test_events_json_and_sse_cursor_resume(client, engine, postgres, peers):
    case_id = _create(client, key="evt-1").json()["case_id"]
    client.post(
        f"/v1/cases/{case_id}/messages",
        headers=auth("token-customer-a"),
        json={"message": "ping", "language": "en-IN", "expected_revision": 1},
    )

    all_events = client.get(
        f"/v1/cases/{case_id}/events?format=json",
        headers=auth("token-customer-a"),
    ).json()["events"]
    assert [e["sequence"] for e in all_events] == [1, 2]

    resumed = client.get(
        f"/v1/cases/{case_id}/events?format=json&after=1",
        headers=auth("token-customer-a"),
    ).json()["events"]
    assert [e["sequence"] for e in resumed] == [2]

    sse = client.get(
        f"/v1/cases/{case_id}/events",
        headers={**auth("token-customer-a"), "Last-Event-ID": "1"},
    )
    assert sse.status_code == 200
    assert "id: 2" in sse.text
    assert "data:" in sse.text

    # Restart durability: new engine/app against same database resumes cursor.
    engine.dispose()
    fresh = create_engine(postgres.url, hide_parameters=True)
    from pathlib import Path

    from sentinel_api.adapters.db.repository import SqlCaseRepository
    from sentinel_api.adapters.http.app import create_app
    from sentinel_api.adapters.http.auth import TokenMap
    from sentinel_api.application.service import CaseService
    from sentinel_api.bootstrap import SecureIds, SystemClock

    repo = SqlCaseRepository(fresh)
    service = CaseService(
        repo=repo,
        clock=SystemClock(),
        ids=SecureIds(),
        workflow=peers["workflow"],
        evidence=peers["evidence"],
        ledger=peers["ledger"],
        verifier=peers["verifier"],
        service_authorization="Bearer token-case-api-service",
    )
    tokens = TokenMap.from_path(
        Path(__file__).resolve().parents[2] / "fixtures" / "auth_tokens.json"
    )
    restarted = create_app(
        service=service,
        tokens=tokens,
        mode="fixture",
        readiness=lambda: {"ready": True, "mode": "fixture"},
    )
    from fastapi.testclient import TestClient

    with TestClient(restarted) as c2:
        after = c2.get(
            f"/v1/cases/{case_id}/events?format=json&after=1",
            headers=auth("token-customer-a"),
        ).json()["events"]
        assert [e["sequence"] for e in after] == [2]
    fresh.dispose()


def test_ops_queue_evidence_escalate_and_decision_proxy(client, app):
    case_id = _create(client, key="ops-1").json()["case_id"]

    # Put case into waiting approval with action via internal result.
    result = client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-workflow"),
        json={
            "event_key": "result-demo-1",
            "expected_revision": 1,
            "status": "WAITING_APPROVAL",
            "evidence_ids": ["evidence-payment-b", "evidence-order"],
            "action_id": "action-demo-1",
            "reason_code": "SUPERVISOR_REQUIRED",
        },
    )
    assert result.status_code == 200
    assert result.json()["revision"] == 2
    assert result.json()["action_id"] == "action-demo-1"

    queue = client.get("/v1/ops/cases?status=WAITING_APPROVAL", headers=auth("token-operator"))
    assert queue.status_code == 200
    assert any(c["case_id"] == case_id for c in queue.json()["cases"])

    evidence = client.get(f"/v1/ops/cases/{case_id}/evidence", headers=auth("token-operator"))
    assert evidence.status_code == 200
    assert evidence.json()["case_id"] == case_id

    decision_body = {
        "decision": "APPROVE",
        "action_digest": "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
        "case_revision": 1,
        "policy_version": "demo-policy-v1",
        "expires_at": "2099-01-01T00:00:00Z",
    }
    decision = client.post(
        "/v1/ops/actions/action-demo-1/decisions",
        headers=auth("token-supervisor"),
        json=decision_body,
    )
    assert decision.status_code == 200
    approval = decision.json()
    assert approval["reviewer_id"] == "token-supervisor"
    assert approval["action_digest"] == decision_body["action_digest"]
    assert approval["case_revision"] == 1
    assert app.state.peers["ledger"].last_authorization == "Bearer token-supervisor"
    assert app.state.peers["ledger"].last_request is not None
    assert app.state.peers["ledger"].last_request.action_digest == decision_body["action_digest"]
    assert any(c.event == "DECISION" for c in app.state.peers["workflow"].calls)

    # Operator cannot decide.
    forbidden = client.post(
        "/v1/ops/actions/action-demo-1/decisions",
        headers=auth("token-operator"),
        json=decision_body,
    )
    assert forbidden.status_code == 403

    # Unknown action in tenant → 404 before ledger call.
    app.state.peers["ledger"].last_request = None
    app.state.peers["ledger"].last_authorization = None
    unknown = client.post(
        "/v1/ops/actions/action-missing/decisions",
        headers=auth("token-supervisor"),
        json=decision_body,
    )
    assert unknown.status_code == 404
    assert app.state.peers["ledger"].last_request is None
    assert app.state.peers["ledger"].last_authorization is None

    escalated = client.post(
        f"/v1/ops/cases/{case_id}/escalate",
        headers=auth("token-operator"),
        json={
            "expected_revision": 2,
            "reason_code": "CUSTOMER_ESCALATION",
            "owner_queue": "SUPERVISOR",
        },
    )
    assert escalated.status_code == 200
    assert escalated.json()["status"] == "ESCALATED"
    assert escalated.json()["revision"] == 3


def test_result_idempotency_and_verified_resolution(client, app):
    case_id = _create(client, key="res-1").json()["case_id"]
    payload = {
        "event_key": "result-demo-1",
        "expected_revision": 1,
        "status": "WAITING_APPROVAL",
        "evidence_ids": ["evidence-payment-b"],
        "action_id": "action-demo-1",
        "reason_code": "SUPERVISOR_REQUIRED",
    }
    first = client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-workflow"),
        json=payload,
    )
    assert first.status_code == 200
    assert first.json()["revision"] == 2

    replay = client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-workflow"),
        json=payload,
    )
    assert replay.status_code == 200
    assert replay.json() == first.json()

    conflict = client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-workflow"),
        json={**payload, "reason_code": "OTHER"},
    )
    assert conflict.status_code == 409

    stale = client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-workflow"),
        json={
            "event_key": "result-demo-2",
            "expected_revision": 1,
            "status": "EXECUTING",
            "evidence_ids": ["evidence-payment-b"],
            "action_id": "action-demo-1",
            "reason_code": "GO",
        },
    )
    assert stale.status_code == 409

    # Body alone cannot close without trusted assessment.
    bare = client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-verifier"),
        json={
            "event_key": "result-verified",
            "expected_revision": 2,
            "status": "VERIFIED_RESOLVED",
            "evidence_ids": ["evidence-payment-b"],
            "action_id": "action-demo-1",
            "reason_code": "CREDITED",
        },
    )
    assert bare.status_code == 422

    assessment = sample_verified_assessment(
        assessment_id="assess-1",
        case_id=case_id,
        case_revision=2,
        action_id="action-demo-1",
    )
    app.state.peers["verifier"].assessments["assess-1"] = assessment
    verified = client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-verifier"),
        json={
            "event_key": "result-verified",
            "expected_revision": 2,
            "status": "VERIFIED_RESOLVED",
            "evidence_ids": ["evidence-payment-b", "evidence-credit"],
            "action_id": "action-demo-1",
            "assessment_id": "assess-1",
            "reason_code": "CREDITED",
        },
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "VERIFIED_RESOLVED"
    assert verified.json()["revision"] == 3


def test_claim_workflow_jobs_exclusive(engine):
    """Atomic claim marks PENDING → CLAIMED; second claim gets nothing."""
    from sqlalchemy import text

    from sentinel_api.adapters.db.repository import SqlCaseRepository
    from sentinel_api.domain.types import WorkflowRequest

    repo = SqlCaseRepository(engine)
    request = WorkflowRequest(
        case_id="case-claim",
        case_revision=1,
        job_key="job-claim-1",
        event="START",
    )
    repo.enqueue_workflow(tenant_id="tenant-demo", request=request)

    first = repo.claim_workflow_jobs(limit=10)
    assert len(first) == 1
    assert first[0][1].job_key == "job-claim-1"

    with engine.connect() as conn:
        status = conn.execute(
            text("SELECT status FROM workflow_outbox WHERE job_key = :k"),
            {"k": "job-claim-1"},
        ).scalar_one()
    assert status == "CLAIMED"

    second = repo.claim_workflow_jobs(limit=10)
    assert second == []


def test_real_peer_http_clients_reject_bad_peers():
    import httpx

    from sentinel_api.adapters.peers.errors import PeerError
    from sentinel_api.adapters.peers.http_clients import HttpEvidenceClient, HttpWorkflowClient
    from sentinel_api.domain.types import WorkflowRequest

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/missing"):
            return httpx.Response(503, json={"code": "DOWN"})
        if "unauthorized" in str(request.url):
            return httpx.Response(403, json={"code": "FORBIDDEN"})
        return httpx.Response(200, json={"not": "ack"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://peer.test")
    workflow = HttpWorkflowClient("http://peer.test", client=client)
    with pytest.raises(PeerError):
        workflow.start_run(
            WorkflowRequest(case_id="c", case_revision=1, job_key="j", event="START"),
            authorization="Bearer t",
        )

    evidence = HttpEvidenceClient("http://peer.test", client=client)

    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN"})

    bad = httpx.Client(transport=httpx.MockTransport(auth_handler), base_url="http://peer.test")
    with pytest.raises(PeerError) as exc:
        HttpEvidenceClient("http://peer.test", client=bad).get_case_evidence(
            "c1", authorization="Bearer t"
        )
    assert exc.value.code == "PEER_UNAUTHORIZED"
    _ = evidence
    _ = json
