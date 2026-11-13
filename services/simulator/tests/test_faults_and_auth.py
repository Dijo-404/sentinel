from __future__ import annotations

from tokens import ADMIN, DISPATCHER, REFUND_BODY, WORKFLOW


def test_capabilities_and_health(client) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready["status"] == "ready"
    assert ready["evidence_mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps == {
        "contract_version": "sentinel.task-contracts.v1",
        "component": "sentinel-simulator",
        "mode": "fixture",
    }


def test_unauthorized_and_wrong_role(client) -> None:
    assert client.get("/v1/orders/DEMO-ORDER-42").status_code == 403
    assert client.get("/v1/orders/DEMO-ORDER-42", headers=DISPATCHER).status_code == 403
    assert (
        client.post(
            "/v1/refunds",
            headers={**WORKFLOW, "Idempotency-Key": "refund-demo-1"},
            json=REFUND_BODY,
        ).status_code
        == 403
    )
    denied = client.put("/v1/admin/faults", headers=WORKFLOW, json={"outage": True})
    assert denied.status_code == 403


def test_idempotency_conflict_on_different_payload(client) -> None:
    first = client.post(
        "/v1/refunds",
        headers={**DISPATCHER, "Idempotency-Key": "refund-demo-1"},
        json=REFUND_BODY,
    )
    assert first.status_code == 202
    conflict = client.post(
        "/v1/refunds",
        headers={**DISPATCHER, "Idempotency-Key": "refund-demo-1"},
        json={**REFUND_BODY, "amount_minor": 100},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_outage_returns_503(client) -> None:
    client.put("/v1/admin/faults", headers=ADMIN, json={"outage": True})
    response = client.get("/v1/orders/DEMO-ORDER-42", headers=WORKFLOW)
    assert response.status_code == 503
    assert response.json()["code"] == "PROVIDER_OUTAGE"
    client.post("/v1/admin/faults/reset", headers=ADMIN)
    assert client.get("/v1/orders/DEMO-ORDER-42", headers=WORKFLOW).status_code == 200


def test_duplicate_and_out_of_order_events(client) -> None:
    client.post(
        "/v1/refunds",
        headers={**DISPATCHER, "Idempotency-Key": "refund-demo-1"},
        json=REFUND_BODY,
    )
    client.put(
        "/v1/admin/faults",
        headers=ADMIN,
        json={"duplicate_events": True, "out_of_order_credit": True},
    )
    confirm = client.post("/v1/admin/refunds/refund-demo-1/confirm", headers=ADMIN)
    assert confirm.status_code == 200
    events = client.get("/v1/admin/events", headers=ADMIN).json()["events"]
    assert events[0]["type"] == "CREDIT_STATUS"
    assert events[0]["payload_status"] == "CLAIMED_UNCONFIRMED"
    assert events[1]["type"] == "REFUND_STATUS"
    assert events[2]["type"] == "REFUND_STATUS"
    assert events[1]["event_id"] != events[2]["event_id"]
    # Out-of-order credit event does not create confirmed credit state.
    assert client.get("/v1/credits/refund-demo-1", headers=WORKFLOW).status_code == 404


def test_delay_fault_applies(client) -> None:
    client.put("/v1/admin/faults", headers=ADMIN, json={"delay_ms": 20})
    response = client.get("/v1/orders/DEMO-ORDER-42", headers=WORKFLOW)
    assert response.status_code == 200


def test_idempotency_key_must_match_provider_ref(client) -> None:
    response = client.post(
        "/v1/refunds",
        headers={**DISPATCHER, "Idempotency-Key": "other-key"},
        json=REFUND_BODY,
    )
    assert response.status_code == 422
