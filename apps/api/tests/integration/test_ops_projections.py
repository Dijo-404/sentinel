"""Ops read projections: messages inbox, history filter, audit events."""

from __future__ import annotations

from tests.conftest import auth

CREATE = {
    "message": "I was charged twice for DEMO-ORDER-42",
    "language": "en-IN",
    "order_reference": "subject-a/DEMO-ORDER-42",
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


def test_ops_history_status_filter(client):
    open_case = _create(client, key="ops-hist-open").json()["case_id"]
    closed_case = _create(client, key="ops-hist-closed").json()["case_id"]

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

    history = client.get("/v1/ops/cases?status=HISTORY", headers=auth("token-supervisor"))
    assert history.status_code == 200
    case_ids = {c["case_id"] for c in history.json()["cases"]}
    assert closed_case in case_ids
    assert open_case not in case_ids

    explicit = client.get(
        "/v1/ops/cases?status=CLOSED_NO_ACTION",
        headers=auth("token-operator"),
    )
    assert explicit.status_code == 200
    assert any(c["case_id"] == closed_case for c in explicit.json()["cases"])


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
