"""Issue #144 follow-ups: ledger error codes reach case results; failed jobs retry on redelivery."""

from __future__ import annotations

import logging
import threading
import time

from fastapi.testclient import TestClient

from sentinel_workflow.application.errors import PeerError
from sentinel_workflow.domain.types import Approval, Principal, WorkflowRequest
from sentinel_workflow.graph.nodes import _peer_reason
from tests.helpers import build_test_app
from tests.stubs import StubCaseApi, StubLedger

AUTH = {"Authorization": "Bearer case-api-token"}


def _run(client, job_key: str, event: str, revision: int = 1):
    return client.post(
        "/v1/runs",
        headers=AUTH,
        json={
            "case_id": "case-demo-42",
            "case_revision": revision,
            "job_key": job_key,
            "event": event,
        },
    )


def _start_and_approve(client, ledger: StubLedger, peers, prefix: str) -> str:
    assert _run(client, f"{prefix}-start", "START").status_code == 202
    action_id = peers["case_api"].results[-1].action_id
    assert action_id
    ledger.attach_approval(
        action_id,
        Approval(
            approval_id=f"approval-{prefix}",
            action_digest=ledger.get_action(action_id).action_digest,
            case_revision=1,
            policy_version="demo-policy-v1",
            decision="APPROVE",
            reviewer_id="supervisor-demo",
            expires_at="2026-11-14T00:00:00Z",
        ),
    )
    return action_id


class ExpiredApprovalLedger(StubLedger):
    def reserve(self, request):
        # Same PeerError HttpLedger raises for a 409 body {"code": "APPROVAL_EXPIRED"}.
        raise PeerError("APPROVAL_EXPIRED", "approval expired", 409)


class DeniedProposalLedger(StubLedger):
    def create_proposal(self, request):
        raise PeerError("POLICY_DENIED", "policy denied", 409)


def test_ledger_409_code_reaches_case_result_and_log(session_factory, caplog):
    ledger = ExpiredApprovalLedger()
    app, _service, peers = build_test_app(session_factory=session_factory, ledger=ledger)
    client = TestClient(app)
    _start_and_approve(client, ledger, peers, "ledger-code")
    with caplog.at_level(logging.WARNING, logger="sentinel_workflow.graph.nodes"):
        assert _run(client, "ledger-code-resume", "DECISION").status_code == 202
    last = peers["case_api"].results[-1]
    assert (last.status, last.reason_code) == ("ESCALATED", "LEDGER_APPROVAL_EXPIRED")
    assert any(
        "code=APPROVAL_EXPIRED" in r.getMessage() and r.levelno == logging.WARNING
        for r in caplog.records
    )


def test_ledger_proposal_409_code_reaches_case_result(session_factory):
    app, _service, peers = build_test_app(
        session_factory=session_factory, ledger=DeniedProposalLedger()
    )
    assert _run(TestClient(app), "ledger-deny-start", "START").status_code == 202
    last = peers["case_api"].results[-1]
    assert (last.status, last.reason_code) == ("ESCALATED", "LEDGER_POLICY_DENIED")


def test_peer_reason_falls_back_for_uncoded_or_unsafe_errors():
    from sentinel_workflow.application.errors import PeerUnavailableError

    unavailable = PeerUnavailableError("action-ledger")
    assert _peer_reason("LEDGER", unavailable, "LEDGER_PEER_FAILURE") == "LEDGER_PEER_FAILURE"
    unsafe = PeerError("bad code\nINJECT", "x", 409)
    assert _peer_reason("LEDGER", unsafe, "LEDGER_PEER_FAILURE") == "LEDGER_PEER_FAILURE"


def test_failed_start_reexecutes_on_same_payload_redelivery(session_factory):
    case_api = StubCaseApi(behavior="unavailable")
    app, service, peers = build_test_app(session_factory=session_factory, case_api=case_api)
    client = TestClient(app)
    assert _run(client, "retry-start", "START").status_code == 503
    assert service.jobs.get_job("tenant-demo", "retry-start")["status"] == "failed"

    case_api.behavior = "valid"
    assert _run(client, "retry-start", "START").status_code == 202
    assert service.jobs.get_job("tenant-demo", "retry-start")["status"] == "completed"
    assert peers["case_api"].results[-1].status == "WAITING_APPROVAL"


def test_failed_decision_resume_reexecutes_with_ledger_approval(session_factory):
    ledger = StubLedger()
    app, service, peers = build_test_app(session_factory=session_factory, ledger=ledger)
    client = TestClient(app)
    _start_and_approve(client, ledger, peers, "retry-decision")

    ledger.behavior = "unavailable"
    assert _run(client, "retry-decision-resume", "DECISION").status_code == 503
    job = service.jobs.get_job("tenant-demo", "retry-decision-resume")
    assert job["status"] == "failed"
    assert ledger.reserve_calls == 0

    ledger.behavior = "valid"
    assert _run(client, "retry-decision-resume", "DECISION").status_code == 202
    assert ledger.reserve_calls == 1
    assert service.jobs.get_job("tenant-demo", "retry-decision-resume")["status"] == "completed"


def test_completed_job_not_reexecuted_and_different_payload_conflicts(session_factory):
    app, service, _peers = build_test_app(session_factory=session_factory)
    client = TestClient(app)
    assert _run(client, "done-start", "START").status_code == 202
    calls: list[str] = []
    service.execute = lambda **kw: calls.append(kw["job_id"])  # type: ignore[method-assign]
    assert _run(client, "done-start", "START").status_code == 202
    assert calls == []
    conflict = _run(client, "done-start", "START", revision=2)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_concurrent_redelivery_of_failed_job_executes_once(session_factory):
    case_api = StubCaseApi(behavior="unavailable")
    app, service, _peers = build_test_app(session_factory=session_factory, case_api=case_api)
    assert _run(TestClient(app), "race-start", "START").status_code == 503

    calls: list[str] = []

    def slow_execute(**kw):
        calls.append(kw["job_id"])
        time.sleep(0.3)
        service.jobs.mark_job_status(kw["job_id"], "completed")

    service.execute = slow_execute  # type: ignore[method-assign]
    principal = Principal(
        principal_id="svc-case-api",
        tenant_id="tenant-demo",
        roles=["workflow"],
        subject_refs=[],
        case_ids=["*"],
    )
    request = WorkflowRequest(
        case_id="case-demo-42", case_revision=1, job_key="race-start", event="START"
    )
    barrier = threading.Barrier(2)

    def redeliver():
        barrier.wait()
        service.accept(request, principal)

    threads = [threading.Thread(target=redeliver) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1
    assert service.jobs.get_job("tenant-demo", "race-start")["status"] == "completed"
