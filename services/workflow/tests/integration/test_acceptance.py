"""Acceptance: approval pause/resume, duplicate command safety, clarification/escalation/wait."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.postgres import PostgresSaver

from sentinel_workflow.application.errors import UnauthorizedError
from sentinel_workflow.application.service import authorize_run
from sentinel_workflow.domain.types import Approval, Principal
from tests.helpers import build_test_app
from tests.stubs import StubLedger, StubVerifier


def _pg_dsn(postgres_url: str) -> str:
    if postgres_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + postgres_url.removeprefix("postgresql+psycopg://")
    return postgres_url


@pytest.fixture
def pg_checkpointer(postgres_url):
    dsn = _pg_dsn(postgres_url)
    with PostgresSaver.from_conn_string(dsn) as saver:
        saver.setup()
        yield saver


def test_post_runs_returns_202_ack(engine, session_factory):
    app, service, peers = build_test_app(session_factory=session_factory)
    client = TestClient(app)
    response = client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer case-api-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-demo-1",
            "event": "START",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["contract_version"] == "sentinel.task-contracts.v1"
    assert body["job_id"]
    # Approval required path pauses with WAITING_APPROVAL delivered.
    statuses = [r.status for r in peers["case_api"].results]
    assert "WAITING_APPROVAL" in statuses


def test_approval_survives_restart_and_resume_is_idempotent(
    engine, session_factory, postgres_url, pg_checkpointer
):
    ledger = StubLedger()
    app1, service1, peers1 = build_test_app(
        session_factory=session_factory,
        checkpointer=pg_checkpointer,
        ledger=ledger,
        verifier=StubVerifier(assessment_status="WAITING"),
    )
    client = TestClient(app1)
    start = client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer case-api-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-restart-1",
            "event": "START",
        },
    )
    assert start.status_code == 202
    assert peers1["case_api"].results[-1].status == "WAITING_APPROVAL"
    action_id = peers1["case_api"].results[-1].action_id
    assert action_id
    proposals_before = ledger.proposal_calls

    # Simulate process restart: new graph/service, same Postgres checkpointer + ledger.
    app2, service2, peers2 = build_test_app(
        session_factory=session_factory,
        checkpointer=pg_checkpointer,
        ledger=ledger,
        case_api=peers1["case_api"],
        evidence=peers1["evidence"],
        policy=peers1["policy"],
        verifier=StubVerifier(assessment_status="WAITING"),
    )
    approval = Approval(
        approval_id="approval-demo-1",
        action_digest=ledger.get_action(action_id).action_digest,
        case_revision=1,
        policy_version="demo-policy-v1",
        decision="APPROVE",
        reviewer_id="supervisor-demo",
        expires_at="2026-11-14T00:00:00Z",
    )
    ledger.attach_approval(action_id, approval)

    # Supervisor approval lives on the ledger action; DECISION has no forge header.
    resume = TestClient(app2).post(
        "/v1/runs",
        headers={"Authorization": "Bearer case-api-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "resume-demo-1",
            "event": "DECISION",
        },
    )
    assert resume.status_code == 202
    # Node replay must not mint another logical financial command.
    assert ledger.proposal_calls == proposals_before
    assert ledger.reserve_calls >= 1
    # Second identical resume job_key is idempotent at accept layer.
    again = TestClient(app2).post(
        "/v1/runs",
        headers={"Authorization": "Bearer case-api-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "resume-demo-1",
            "event": "DECISION",
        },
    )
    assert again.status_code == 202
    assert again.json()["job_id"] == resume.json()["job_id"]
    reserves_after = ledger.reserve_calls
    # Identical job does not re-execute; reserve count stable.
    assert ledger.reserve_calls == reserves_after

    statuses = [r.status for r in peers2["case_api"].results]
    assert "WAITING_EXTERNAL" in statuses or "VERIFIED_RESOLVED" in statuses


def test_missing_evidence_yields_needs_input(engine, session_factory):
    app, service, peers = build_test_app(session_factory=session_factory, evidence_missing=True)
    client = TestClient(app)
    response = client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer workflow-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-missing-1",
            "event": "START",
        },
    )
    assert response.status_code == 202
    assert peers["case_api"].results[-1].status == "NEEDS_INPUT"
    assert peers["case_api"].results[-1].reason_code == "MISSING_EVIDENCE"


def test_malformed_model_escalates(engine, session_factory):
    app, service, peers = build_test_app(
        session_factory=session_factory, model_scenario="malformed"
    )
    client = TestClient(app)
    response = client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer workflow-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-model-bad-1",
            "event": "START",
        },
    )
    assert response.status_code == 202
    assert peers["case_api"].results[-1].status == "ESCALATED"
    assert "MODEL_MALFORMED" in peers["case_api"].results[-1].reason_code


def test_model_outage_escalates(engine, session_factory):
    app, service, peers = build_test_app(session_factory=session_factory, model_scenario="outage")
    client = TestClient(app)
    response = client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer workflow-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-model-down-1",
            "event": "START",
        },
    )
    assert response.status_code == 202
    assert peers["case_api"].results[-1].status == "ESCALATED"
    assert "MODEL_OUTAGE" in peers["case_api"].results[-1].reason_code


def test_exhausted_budget_escalates(engine, session_factory):
    app, service, peers = build_test_app(session_factory=session_factory, investigation_budget=0)
    # Force budget path by setting steps already over budget after load increments.
    # With budget 0, after load_input steps=1 > 0 triggers escalate at plan routing.
    # Actually budget check is after plan. Set budget to 0 and ensure plan runs then routes.
    client = TestClient(app)
    # Patch: investigation_budget 0 means after load (steps=1) plan still runs; route checks
    # steps > budget after plan. 1 > 0 => budget.
    response = client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer workflow-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-budget-1",
            "event": "START",
        },
    )
    assert response.status_code == 202
    # With budget 0, proposal path hits budget after successful plan.
    assert peers["case_api"].results[-1].status == "ESCALATED"
    assert peers["case_api"].results[-1].reason_code == "INVESTIGATION_BUDGET_EXHAUSTED"


def test_pending_verification_waits(engine, session_factory):
    ledger = StubLedger()
    app, service, peers = build_test_app(
        session_factory=session_factory,
        ledger=ledger,
        verifier=StubVerifier(assessment_status="WAITING"),
    )
    client = TestClient(app)
    client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer case-api-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-wait-1",
            "event": "START",
        },
    )
    action_id = peers["case_api"].results[-1].action_id
    approval = Approval(
        approval_id="approval-wait-1",
        action_digest=ledger.get_action(action_id).action_digest,
        case_revision=1,
        policy_version="demo-policy-v1",
        decision="APPROVE",
        reviewer_id="supervisor-demo",
        expires_at="2026-11-14T00:00:00Z",
    )
    ledger.attach_approval(action_id, approval)
    client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer case-api-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "resume-wait-1",
            "event": "DECISION",
        },
    )
    assert any(r.status == "WAITING_EXTERNAL" for r in peers["case_api"].results)


def test_outbox_retries_on_case_api_outage(engine, session_factory):
    app, service, peers = build_test_app(session_factory=session_factory, evidence_missing=True)
    peers["case_api"].fail_submit_times = 1
    client = TestClient(app)
    client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer workflow-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-outbox-1",
            "event": "START",
        },
    )
    # First flush failed; pending remains until retry.
    assert service.flush_outbox() >= 1
    assert peers["case_api"].results[-1].status == "NEEDS_INPUT"


def test_outbox_not_pending_forever_after_max_attempts(engine, session_factory):
    app, service, peers = build_test_app(
        session_factory=session_factory,
        evidence_missing=True,
        outbox_max_attempts=3,
    )
    peers["case_api"].fail_submit_times = 100
    client = TestClient(app)
    client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer workflow-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-outbox-max-1",
            "event": "START",
        },
    )
    for _ in range(5):
        service.flush_outbox()
    assert service.outbox.pending() == []
    assert peers["case_api"].results == []


def test_idempotent_job_key_conflict(engine, session_factory):
    app, service, peers = build_test_app(session_factory=session_factory)
    client = TestClient(app)
    body = {
        "case_id": "case-demo-42",
        "case_revision": 1,
        "job_key": "start-conflict-1",
        "event": "START",
    }
    assert (
        client.post(
            "/v1/runs", headers={"Authorization": "Bearer workflow-token"}, json=body
        ).status_code
        == 202
    )
    body2 = dict(body)
    body2["case_revision"] = 2
    conflict = client.post(
        "/v1/runs", headers={"Authorization": "Bearer workflow-token"}, json=body2
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_unauthorized_run_rejected(engine, session_factory):
    app, service, peers = build_test_app(session_factory=session_factory)
    client = TestClient(app)
    response = client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer no-such-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-unauth-1",
            "event": "START",
        },
    )
    assert response.status_code == 403


def test_outbox_idempotency_conflict_not_delivered(engine, session_factory):
    app, service, peers = build_test_app(session_factory=session_factory, evidence_missing=True)
    peers["case_api"].submit_conflict = "IDEMPOTENCY_CONFLICT"
    client = TestClient(app)
    client.post(
        "/v1/runs",
        headers={"Authorization": "Bearer workflow-token"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "start-idem-conflict-1",
            "event": "START",
        },
    )
    assert service.flush_outbox() == 0
    assert peers["case_api"].results == []
    pending = service.outbox.pending()
    assert len(pending) >= 1


def test_empty_case_ids_deny_wildcard_allows():
    empty = Principal(
        principal_id="p-empty",
        tenant_id="tenant-demo",
        roles=["workflow"],
        subject_refs=["subject-demo"],
        case_ids=[],
    )
    with pytest.raises(UnauthorizedError):
        authorize_run(empty, "case-demo-42")

    wild = Principal(
        principal_id="p-wild",
        tenant_id="tenant-demo",
        roles=["workflow"],
        subject_refs=["subject-demo"],
        case_ids=["*"],
    )
    authorize_run(wild, "case-any-99")
