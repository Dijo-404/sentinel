"""Ops read projections: messages inbox, history filter, audit events."""

from __future__ import annotations

from sentinel_api.adapters.peers.fixture_clients import sample_verified_assessment
from tests.conftest import auth

CREATE = {
    "message": "I was charged twice for DEMO-ORDER-42",
    "language": "en-IN",
    "order_reference": "subject-a/DEMO-ORDER-42",
    "channel": "web",
}

OTHER_CREATE = {
    "message": "Other tenant dispute",
    "language": "en-IN",
    "order_reference": "subject-x/OTHER-ORDER-1",
    "channel": "web",
}


def _create(client, token="token-customer-a", key="ops-proj-1", body=None):
    return client.post(
        "/v1/cases",
        headers={**auth(token), "Idempotency-Key": key},
        json=body or CREATE,
    )


def test_ops_messages_lists_seeded_message(client):
    created = _create(client).json()
    case_id = created["case_id"]

    response = client.get("/v1/ops/messages", headers=auth("token-operator"))
    assert response.status_code == 200
    body = response.json()
    assert "messages" in body
    assert isinstance(body["messages"], list)
    assert len(body["messages"]) >= 1

    match = next(m for m in body["messages"] if m["case_id"] == case_id)
    assert match["message_id"]
    assert match["text"] == CREATE["message"]
    assert match["language"] == CREATE["language"]
    assert match["author"] == "CUSTOMER"
    assert match["occurred_at"]
    assert len(body["messages"]) <= 50

    supervisor = client.get("/v1/ops/messages", headers=auth("token-supervisor"))
    assert supervisor.status_code == 200
    assert any(m["case_id"] == case_id for m in supervisor.json()["messages"])


def test_ops_history_status_filter(client, app):
    open_case = _create(client, key="ops-hist-open").json()["case_id"]
    closed_case = _create(client, key="ops-hist-closed").json()["case_id"]
    verified_case = _create(client, key="ops-hist-verified").json()["case_id"]

    close = client.post(
        f"/v1/internal/cases/{closed_case}/results",
        headers=auth("token-workflow"),
        json={
            "event_key": "close-no-action-1",
            "expected_revision": 1,
            "status": "CLOSED_NO_ACTION",
            "evidence_ids": [],
            "reason_code": "NO_ACTION",
        },
    )
    assert close.status_code == 200
    assert close.json()["status"] == "CLOSED_NO_ACTION"

    assessment = sample_verified_assessment(
        assessment_id="assess-hist-1",
        case_id=verified_case,
        case_revision=1,
        action_id="action-hist-1",
    )
    app.state.peers["verifier"].assessments["assess-hist-1"] = assessment
    verified = client.post(
        f"/v1/internal/cases/{verified_case}/results",
        headers=auth("token-verifier"),
        json={
            "event_key": "hist-verified-1",
            "expected_revision": 1,
            "status": "VERIFIED_RESOLVED",
            "evidence_ids": ["evidence-payment-b", "evidence-credit"],
            "action_id": "action-hist-1",
            "assessment_id": "assess-hist-1",
            "reason_code": "CREDITED",
        },
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "VERIFIED_RESOLVED"

    history = client.get("/v1/ops/cases?status=HISTORY", headers=auth("token-supervisor"))
    assert history.status_code == 200
    by_id = {c["case_id"]: c["status"] for c in history.json()["cases"]}
    assert by_id.get(closed_case) == "CLOSED_NO_ACTION"
    assert by_id.get(verified_case) == "VERIFIED_RESOLVED"
    assert open_case not in by_id
    assert set(by_id.values()) <= {"VERIFIED_RESOLVED", "CLOSED_NO_ACTION"}

    explicit_closed = client.get(
        "/v1/ops/cases?status=CLOSED_NO_ACTION",
        headers=auth("token-operator"),
    )
    assert explicit_closed.status_code == 200
    assert any(c["case_id"] == closed_case for c in explicit_closed.json()["cases"])

    explicit_verified = client.get(
        "/v1/ops/cases?status=VERIFIED_RESOLVED",
        headers=auth("token-operator"),
    )
    assert explicit_verified.status_code == 200
    assert any(c["case_id"] == verified_case for c in explicit_verified.json()["cases"])


def test_ops_audit_events_lists_seeded_event(client):
    case_id = _create(client, key="ops-audit-1").json()["case_id"]

    response = client.get("/v1/ops/audit-events", headers=auth("token-supervisor"))
    assert response.status_code == 200
    body = response.json()
    assert "events" in body
    assert isinstance(body["events"], list)
    assert len(body["events"]) >= 1

    match = next(e for e in body["events"] if e["case_id"] == case_id)
    assert isinstance(match["sequence"], int)
    assert match["type"] == "CASE_CREATED"
    assert match["occurred_at"]
    assert isinstance(match["payload"], dict)
    assert len(body["events"]) <= 50


def test_ops_projections_forbid_customer(client):
    _create(client, key="ops-forbid-1")

    messages = client.get("/v1/ops/messages", headers=auth("token-customer-a"))
    assert messages.status_code == 403

    audit = client.get("/v1/ops/audit-events", headers=auth("token-customer-a"))
    assert audit.status_code == 403

    history = client.get("/v1/ops/cases?status=HISTORY", headers=auth("token-customer-a"))
    assert history.status_code == 403


def test_ops_projections_cross_tenant_isolation(client):
    tenant_a = _create(client, key="ops-tenant-a").json()["case_id"]
    close_a = client.post(
        f"/v1/internal/cases/{tenant_a}/results",
        headers=auth("token-workflow"),
        json={
            "event_key": "close-tenant-a",
            "expected_revision": 1,
            "status": "CLOSED_NO_ACTION",
            "evidence_ids": [],
            "reason_code": "NO_ACTION",
        },
    )
    assert close_a.status_code == 200

    tenant_other = _create(
        client,
        token="token-customer-other-tenant",
        key="ops-tenant-other",
        body=OTHER_CREATE,
    ).json()["case_id"]
    close_other = client.post(
        f"/v1/internal/cases/{tenant_other}/results",
        headers=auth("token-workflow-other-tenant"),
        json={
            "event_key": "close-tenant-other",
            "expected_revision": 1,
            "status": "CLOSED_NO_ACTION",
            "evidence_ids": [],
            "reason_code": "NO_ACTION",
        },
    )
    assert close_other.status_code == 200

    for token in ("token-operator-other-tenant", "token-supervisor-other-tenant"):
        messages = client.get("/v1/ops/messages", headers=auth(token))
        assert messages.status_code == 200
        msg_ids = {m["case_id"] for m in messages.json()["messages"]}
        assert tenant_a not in msg_ids
        assert tenant_other in msg_ids

        audit = client.get("/v1/ops/audit-events", headers=auth(token))
        assert audit.status_code == 200
        event_ids = {e["case_id"] for e in audit.json()["events"]}
        assert tenant_a not in event_ids
        assert tenant_other in event_ids

        history = client.get("/v1/ops/cases?status=HISTORY", headers=auth(token))
        assert history.status_code == 200
        hist_ids = {c["case_id"] for c in history.json()["cases"]}
        assert tenant_a not in hist_ids
        assert tenant_other in hist_ids

    demo_messages = client.get("/v1/ops/messages", headers=auth("token-operator"))
    assert demo_messages.status_code == 200
    demo_msg_ids = {m["case_id"] for m in demo_messages.json()["messages"]}
    assert tenant_a in demo_msg_ids
    assert tenant_other not in demo_msg_ids

    demo_audit = client.get("/v1/ops/audit-events", headers=auth("token-supervisor"))
    assert demo_audit.status_code == 200
    demo_event_ids = {e["case_id"] for e in demo_audit.json()["events"]}
    assert tenant_a in demo_event_ids
    assert tenant_other not in demo_event_ids

    demo_history = client.get("/v1/ops/cases?status=HISTORY", headers=auth("token-supervisor"))
    assert demo_history.status_code == 200
    demo_hist_ids = {c["case_id"] for c in demo_history.json()["cases"]}
    assert tenant_a in demo_hist_ids
    assert tenant_other not in demo_hist_ids
