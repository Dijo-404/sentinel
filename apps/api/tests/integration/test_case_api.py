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
    "order_reference": "subject-a/DEMO-ORDER-42",
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


def test_customer_cannot_create_case_on_unbound_order(client):
    """subject_ref comes from principal; order_reference must still be bound."""
    victim = _create(
        client,
        key="victim-order",
        body={**CREATE, "order_reference": "subject-b/VICTIM-ORDER"},
    )
    assert victim.status_code == 403
    assert victim.json()["code"] == "FORBIDDEN"

    unbound = _create(
        client,
        key="unbound-order",
        body={**CREATE, "order_reference": "DEMO-ORDER-42"},
    )
    assert unbound.status_code == 403
    assert unbound.json()["code"] == "FORBIDDEN"


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

    evidence_peer = app.state.peers["evidence"]
    seen_auth: list[str] = []
    original_get = evidence_peer.get_case_evidence

    def recording_get(cid, *, authorization):
        seen_auth.append(authorization)
        return original_get(cid, authorization=authorization)

    evidence_peer.get_case_evidence = recording_get
    evidence = client.get(f"/v1/ops/cases/{case_id}/evidence", headers=auth("token-operator"))
    assert evidence.status_code == 200
    assert evidence.json()["case_id"] == case_id
    # Evidence.v1 trusts service bearers only; portal/operator tokens are not forwarded.
    assert seen_auth == ["Bearer token-case-api-service"]

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
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import text

    from sentinel_api.adapters.db.repository import SqlCaseRepository
    from sentinel_api.domain.types import WorkflowRequest

    repo = SqlCaseRepository(engine)
    request = WorkflowRequest(
        case_id="case-claim",
        case_revision=1,
        job_key="job-claim-1",
        event="START",
        order_reference="subject-a/DEMO-ORDER-42",
    )
    repo.enqueue_workflow(tenant_id="tenant-demo", request=request)

    now = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)
    first = repo.claim_workflow_jobs(limit=10, now=now)
    assert len(first) == 1
    assert first[0][1].job_key == "job-claim-1"
    assert first[0][1].order_reference == "subject-a/DEMO-ORDER-42"

    with engine.connect() as conn:
        status = conn.execute(
            text("SELECT status FROM workflow_outbox WHERE job_key = :k"),
            {"k": "job-claim-1"},
        ).scalar_one()
    assert status == "CLAIMED"

    # Active lease: not reclaimable yet.
    second = repo.claim_workflow_jobs(limit=10, now=now + timedelta(seconds=5))
    assert second == []


def test_stale_claimed_workflow_job_reclaimed_after_lease_expiry(engine):
    """Simulated crash: CLAIMED with expired lease becomes claimable again."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import text

    from sentinel_api.adapters.db.repository import (
        WORKFLOW_JOB_LEASE_SECONDS,
        SqlCaseRepository,
    )
    from sentinel_api.domain.types import WorkflowRequest

    repo = SqlCaseRepository(engine)
    request = WorkflowRequest(
        case_id="case-crash",
        case_revision=1,
        job_key="job-crash-1",
        event="START",
        order_reference="subject-a/DEMO-ORDER-42",
    )
    repo.enqueue_workflow(tenant_id="tenant-demo", request=request)

    claimed_at = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)
    first = repo.claim_workflow_jobs(limit=10, now=claimed_at)
    assert len(first) == 1
    # Crash: leave CLAIMED; do not mark DELIVERED.

    after_lease = claimed_at + timedelta(seconds=WORKFLOW_JOB_LEASE_SECONDS + 1)
    recovered = repo.claim_workflow_jobs(limit=10, now=after_lease)
    assert len(recovered) == 1
    assert recovered[0][1].job_key == "job-crash-1"
    assert recovered[0][1].order_reference == "subject-a/DEMO-ORDER-42"

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, lease_expires_at FROM workflow_outbox WHERE job_key = :k"),
            {"k": "job-crash-1"},
        ).one()
    assert row[0] == "CLAIMED"
    assert row[1] is not None


def test_create_case_enqueues_start_job_atomically(engine):
    """Case row and START outbox share one transaction (no separate enqueue race)."""
    from sqlalchemy import text

    from sentinel_api.adapters.db.repository import SqlCaseRepository
    from sentinel_api.domain.types import CaseCreate, Principal, WorkflowRequest

    repo = SqlCaseRepository(engine)
    principal = Principal(
        principal_id="cust-a",
        tenant_id="tenant-demo",
        roles=("customer",),
        subject_refs=("subject-a",),
        case_ids=(),
    )
    create = CaseCreate(
        message="charged twice",
        language="en-IN",
        order_reference="subject-a/DEMO-ORDER-42",
        channel="web",
    )
    start_job = WorkflowRequest(
        case_id="case-atomic-1",
        case_revision=1,
        job_key="start:case-atomic-1:1",
        event="START",
        order_reference=create.order_reference,
    )
    created, case, reused = repo.create_case(
        principal=principal,
        create=create,
        idempotency_key="atomic-1",
        case_id="case-atomic-1",
        message_id="msg-1",
        event_id="evt-1",
        occurred_at="2026-11-14T12:00:00Z",
        start_job=start_job,
    )
    assert not reused
    assert created.case_id == "case-atomic-1"
    assert case.case_id == "case-atomic-1"

    with engine.connect() as conn:
        status = conn.execute(
            text("SELECT status FROM workflow_outbox WHERE job_key = :k"),
            {"k": "start:case-atomic-1:1"},
        ).scalar_one()
        payload = conn.execute(
            text("SELECT payload_json FROM workflow_outbox WHERE job_key = :k"),
            {"k": "start:case-atomic-1:1"},
        ).scalar_one()
    assert status == "PENDING"
    assert json.loads(payload)["order_reference"] == "subject-a/DEMO-ORDER-42"


def test_canonical_order_reference_preserved_through_input_and_outbox(client, app):
    """Intake subject-prefixed order_reference is not stripped for CaseInput or START outbox."""
    canonical = "subject-a/DEMO-ORDER-42"
    assert CREATE["order_reference"] == canonical

    created = _create(client, key="order-preserve-1").json()
    case_id = created["case_id"]

    snap = client.get(
        f"/v1/internal/cases/{case_id}/input?revision=1",
        headers=auth("token-workflow"),
    )
    assert snap.status_code == 200
    assert snap.json()["order_reference"] == canonical

    start_calls = [c for c in app.state.peers["workflow"].calls if c.event == "START"]
    assert start_calls
    assert start_calls[0].order_reference == canonical
    # Wire body omits order_reference; CaseInput carries the authorized identity.
    assert "order_reference" not in start_calls[0].to_wire_dict()


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


def test_auth06_operator_cannot_call_supervisor_decision(client, app):
    """AUTH-06: operator decision path → 403; ledger untouched."""
    case_id = _create(client, key="auth06").json()["case_id"]
    client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-workflow"),
        json={
            "event_key": "auth06-waiting",
            "expected_revision": 1,
            "status": "WAITING_APPROVAL",
            "evidence_ids": ["evidence-payment-b"],
            "action_id": "action-auth06",
            "reason_code": "SUPERVISOR_REQUIRED",
        },
    )
    app.state.peers["ledger"].last_request = None
    app.state.peers["ledger"].last_authorization = None
    forbidden = client.post(
        "/v1/ops/actions/action-auth06/decisions",
        headers=auth("token-operator"),
        json={
            "decision": "APPROVE",
            "action_digest": "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
            "case_revision": 2,
            "policy_version": "demo-policy-v1",
            "expires_at": "2099-01-01T00:00:00Z",
        },
    )
    assert forbidden.status_code == 403
    assert app.state.peers["ledger"].last_request is None
    assert app.state.peers["ledger"].last_authorization is None


@pytest.mark.parametrize(
    "token",
    ["token-risk-officer", "token-platform-admin", "token-merchant"],
)
def test_sn040_extended_humans_cannot_call_supervisor_decision(client, app, token):
    """SN-040: risk_officer / platform_admin / merchant are not supervisors for decide."""
    case_id = _create(client, key=f"sn040-{token}").json()["case_id"]
    client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-workflow"),
        json={
            "event_key": f"sn040-waiting-{token}",
            "expected_revision": 1,
            "status": "WAITING_APPROVAL",
            "evidence_ids": ["evidence-payment-b"],
            "action_id": f"action-sn040-{token}",
            "reason_code": "SUPERVISOR_REQUIRED",
        },
    )
    app.state.peers["ledger"].last_request = None
    app.state.peers["ledger"].last_authorization = None
    forbidden = client.post(
        f"/v1/ops/actions/action-sn040-{token}/decisions",
        headers=auth(token),
        json={
            "decision": "APPROVE",
            "action_digest": "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
            "case_revision": 2,
            "policy_version": "demo-policy-v1",
            "expires_at": "2099-01-01T00:00:00Z",
        },
    )
    assert forbidden.status_code == 403
    assert app.state.peers["ledger"].last_request is None
    assert app.state.peers["ledger"].last_authorization is None


def test_auth08_customer_other_subject_denied(client):
    """AUTH-08: customer cannot read another subject's case."""
    case_id = _create(client, key="auth08").json()["case_id"]
    denied = client.get(f"/v1/cases/{case_id}", headers=auth("token-customer-b"))
    assert denied.status_code == 404
    assert "case_id" not in denied.json()


def test_claim_atomic_conflict(client):
    case_id = _create(client, key="claim-1").json()["case_id"]
    first = client.post(f"/v1/ops/cases/{case_id}/claim", headers=auth("token-operator"))
    assert first.status_code == 200
    assert first.json()["assigned_principal_id"] == "operator-1"
    assert first.json()["revision"] == 2

    replay = client.post(f"/v1/ops/cases/{case_id}/claim", headers=auth("token-operator"))
    assert replay.status_code == 200
    assert replay.json()["assigned_principal_id"] == "operator-1"
    assert replay.json()["revision"] == 2

    conflict = client.post(f"/v1/ops/cases/{case_id}/claim", headers=auth("token-operator-2"))
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "ASSIGNMENT_CONFLICT"

    customer = client.post(f"/v1/ops/cases/{case_id}/claim", headers=auth("token-customer-a"))
    assert customer.status_code == 403


def test_claim_concurrency(client, app):
    """Two concurrent repo claims: exactly one wins; loser gets ASSIGNMENT_CONFLICT."""
    import threading

    from sentinel_api.domain.types import DomainError, Principal

    case_id = _create(client, key="claim-race").json()["case_id"]
    repo = app.state.repo
    outcomes: list[str] = []
    barrier = threading.Barrier(2)
    lock = threading.Lock()

    def claim(principal_id: str) -> None:
        principal = Principal(
            principal_id=principal_id,
            tenant_id="tenant-demo",
            roles=("operator",),
        )
        barrier.wait(timeout=5)
        try:
            repo.claim_case(
                principal=principal,
                case_id=case_id,
                event_id=f"evt-{principal_id}",
                occurred_at="2026-11-14T00:00:00Z",
            )
            with lock:
                outcomes.append("ok")
        except DomainError as exc:
            with lock:
                outcomes.append(exc.code)

    t1 = threading.Thread(target=claim, args=("operator-1",))
    t2 = threading.Thread(target=claim, args=("operator-2",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)
    assert sorted(outcomes) == ["ASSIGNMENT_CONFLICT", "ok"]
    meta = repo.get_case_meta(tenant_id="tenant-demo", case_id=case_id)
    assert meta is not None
    assert meta["assigned_principal_id"] in {"operator-1", "operator-2"}


def test_apply_result_preserves_assigned_principal(client):
    case_id = _create(client, key="claim-preserve").json()["case_id"]
    claimed = client.post(f"/v1/ops/cases/{case_id}/claim", headers=auth("token-operator"))
    assert claimed.status_code == 200
    assert claimed.json()["assigned_principal_id"] == "operator-1"
    revision = claimed.json()["revision"]

    result = client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-workflow"),
        json={
            "event_key": "preserve-assign-1",
            "expected_revision": revision,
            "status": "INVESTIGATING",
            "evidence_ids": ["evidence-payment-b"],
            "reason_code": "CONTINUE",
        },
    )
    assert result.status_code == 200
    assert result.json()["assigned_principal_id"] == "operator-1"

    replay = client.post(
        f"/v1/internal/cases/{case_id}/results",
        headers=auth("token-workflow"),
        json={
            "event_key": "preserve-assign-1",
            "expected_revision": revision,
            "status": "INVESTIGATING",
            "evidence_ids": ["evidence-payment-b"],
            "reason_code": "CONTINUE",
        },
    )
    assert replay.status_code == 200
    assert replay.json()["assigned_principal_id"] == "operator-1"


def test_dashboards_and_identity_session(client):
    case_id = _create(client, key="dash-1").json()["case_id"]

    cust = client.get("/v1/customer/dashboard", headers=auth("token-customer-a"))
    assert cust.status_code == 200
    assert cust.json()["open_cases"] >= 1

    other = client.get("/v1/customer/dashboard", headers=auth("token-customer-b"))
    assert other.status_code == 200
    assert other.json()["open_cases"] == 0

    cases = client.get("/v1/customer/cases", headers=auth("token-customer-a"))
    assert cases.status_code == 200
    assert any(c["case_id"] == case_id for c in cases.json()["cases"])

    op_denied = client.get("/v1/customer/dashboard", headers=auth("token-operator"))
    assert op_denied.status_code == 403

    claimed = client.post(f"/v1/ops/cases/{case_id}/claim", headers=auth("sess-operator-1"))
    assert claimed.status_code == 200
    assert claimed.json()["assigned_principal_id"] == "operator-1"

    op_dash = client.get("/v1/operator/dashboard", headers=auth("sess-operator-1"))
    assert op_dash.status_code == 200
    body = op_dash.json()
    assert body["assigned_to_me"] >= 1
    assert "open_total" in body

    cust_op = client.get("/v1/operator/dashboard", headers=auth("token-customer-a"))
    assert cust_op.status_code == 403

    sup = client.get("/v1/supervisor/dashboard", headers=auth("sess-supervisor-1"))
    assert sup.status_code == 200
    assert "waiting_approval_cases" in sup.json()
    assert "pending_approvals" in sup.json()

    op_sup = client.get("/v1/supervisor/dashboard", headers=auth("token-operator"))
    assert op_sup.status_code == 403
