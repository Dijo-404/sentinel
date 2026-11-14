"""Risk clearance resume endpoint + hold gate. Clearance never approves money."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.helpers import build_test_app
from tests.stubs import StubRisk


def _auth(token: str = "tok-risk-officer") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _cleared_payload(**overrides):
    body = {
        "event_type": "risk.restriction.cleared",
        "investigation_id": "inv-1",
        "case_id": "case-demo-42",
        "restriction_id": "rst-1",
        "tenant_id": "tenant-demo",
        "financial_approval_granted": False,
    }
    body.update(overrides)
    return body


def test_risk_resume_accepts_clearance_and_starts_reeval(session_factory):
    app, service, _peers = build_test_app(session_factory=session_factory)
    client = TestClient(app)
    response = client.post(
        "/v1/workflow/risk-resume",
        headers=_auth(),
        json=_cleared_payload(),
    )
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["job_id"]
    # No forged approval path: DECISION store empty for this thread.
    thread_id = "tenant-demo:case-demo-42:1"
    assert service.decisions.get_decision(thread_id) is None


def test_risk_resume_rejects_financial_approval_flag(session_factory):
    app, _service, _peers = build_test_app(session_factory=session_factory)
    client = TestClient(app)
    response = client.post(
        "/v1/workflow/risk-resume",
        headers=_auth(),
        json=_cleared_payload(financial_approval_granted=True),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_REQUEST"


def test_risk_resume_requires_risk_officer(session_factory):
    app, _service, _peers = build_test_app(session_factory=session_factory)
    client = TestClient(app)
    response = client.post(
        "/v1/workflow/risk-resume",
        headers=_auth("tok-workflow"),
        json=_cleared_payload(),
    )
    assert response.status_code == 403


def test_active_hold_blocks_proposal_path(session_factory):
    app, _service, peers = build_test_app(
        session_factory=session_factory,
        risk=StubRisk(blocked_cases={"case-demo-42"}),
    )
    client = TestClient(app)
    response = client.post(
        "/v1/runs",
        headers=_auth("tok-workflow"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "hold-block-1",
            "event": "START",
        },
    )
    assert response.status_code == 202
    # Hold stops before ledger proposal.
    assert peers["ledger"].proposal_calls == 0
    assert peers["ledger"].reserve_calls == 0
    assert any(r.reason_code == "RISK_HOLD_ACTIVE" for r in peers["case_api"].results)


def test_risk_peer_unavailable_fails_closed(session_factory):
    app, _service, peers = build_test_app(
        session_factory=session_factory,
        risk=StubRisk(behavior="unavailable"),
    )
    client = TestClient(app)
    response = client.post(
        "/v1/runs",
        headers=_auth("tok-workflow"),
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "job_key": "hold-unavail-1",
            "event": "START",
        },
    )
    assert response.status_code == 202
    assert peers["ledger"].proposal_calls == 0
    assert any(r.reason_code == "RISK_PEER_UNAVAILABLE" for r in peers["case_api"].results)
