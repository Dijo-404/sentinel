"""Acceptance: health, capabilities, threads, messages, auth, sandbox evidence."""

from __future__ import annotations

from tests.conftest import auth


def test_health_and_capabilities(client):
    health = client.get("/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    caps = client.get("/v1/capabilities")
    assert caps.status_code == 200
    body = caps.json()
    assert body["port"] == "assistant.v1"
    assert body["component"] == "assistant"
    assert body["financial_authority"] is False
    assert body["mode"] == "fixture"


def test_unauthenticated_threads_forbidden(client):
    response = client.get("/v1/threads", params={"role": "customer"})
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_create_list_and_message_flow_customer(client):
    created = client.post(
        "/v1/threads",
        headers=auth("tok-customer"),
        json={"title": "Refund question"},
    )
    assert created.status_code == 200
    thread = created.json()
    assert thread["title"] == "Refund question"
    assert "thread_id" in thread
    assert "updated_at" in thread

    listed = client.get(
        "/v1/threads",
        headers=auth("tok-customer"),
        params={"role": "customer"},
    )
    assert listed.status_code == 200
    threads = listed.json()["threads"]
    assert len(threads) == 1
    assert threads[0]["thread_id"] == thread["thread_id"]

    posted = client.post(
        f"/v1/threads/{thread['thread_id']}/messages",
        headers=auth("tok-customer"),
        json={"text": "Where is my refund?"},
    )
    assert posted.status_code == 200
    message = posted.json()
    assert message["text"] == "Where is my refund?"
    assert message["evidence_mode"] == "sandbox"
    assert message["role"] == "user"

    messages = client.get(
        f"/v1/threads/{thread['thread_id']}/messages",
        headers=auth("tok-customer"),
    )
    assert messages.status_code == 200
    items = messages.json()["messages"]
    assert len(items) >= 1
    assert items[0]["evidence_mode"] == "sandbox"
    assistant = next(m for m in items if m["role"] == "assistant")
    assert assistant["evidence_mode"] == "sandbox"
    assert "Where is my refund?" in assistant["text"]
    assert assistant["text"] != items[0]["text"]


def test_operator_role_filter_separate_from_customer(client):
    client.post(
        "/v1/threads",
        headers=auth("tok-customer"),
        json={"title": "Customer thread"},
    )
    op = client.post(
        "/v1/threads",
        headers=auth("operator-token"),
        json={"title": "Operator thread"},
    )
    assert op.status_code == 200

    customer_list = client.get(
        "/v1/threads",
        headers=auth("tok-customer"),
        params={"role": "customer"},
    ).json()["threads"]
    assert len(customer_list) == 1
    assert customer_list[0]["title"] == "Customer thread"

    operator_list = client.get(
        "/v1/threads",
        headers=auth("operator-token"),
        params={"role": "operator"},
    ).json()["threads"]
    assert len(operator_list) == 1
    assert operator_list[0]["title"] == "Operator thread"


def test_tenant_isolation(client):
    created = client.post(
        "/v1/threads",
        headers=auth("tok-customer"),
        json={"title": "Demo only"},
    )
    thread_id = created.json()["thread_id"]

    listed = client.get(
        "/v1/threads",
        headers=auth("tok-other"),
        params={"role": "customer"},
    )
    assert listed.status_code == 200
    assert listed.json()["threads"] == []

    messages = client.get(
        f"/v1/threads/{thread_id}/messages",
        headers=auth("tok-other"),
    )
    assert messages.status_code == 404


def test_list_requires_role_query(client):
    response = client.get("/v1/threads", headers=auth("tok-customer"))
    assert response.status_code == 422
