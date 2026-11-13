from __future__ import annotations

from tokens import ADMIN, DISPATCHER, REFUND_BODY, VERIFIER, WORKFLOW


def test_two_captured_payments_map_to_one_fulfilled_order(client) -> None:
    order = client.get("/v1/orders/DEMO-ORDER-42", headers=WORKFLOW)
    assert order.status_code == 200
    body = order.json()
    assert body["fulfilled_order_count"] == 1
    assert body["merchant_confirmed_duplicate"] is True
    assert body["paid"] is True
    assert body["subject_ref"] == "subject-demo-42"

    payments = client.get(
        "/v1/transactions",
        params={"order_reference": "DEMO-ORDER-42"},
        headers=WORKFLOW,
    )
    assert payments.status_code == 200
    rows = payments.json()["payments"]
    assert len(rows) == 2
    assert {row["transaction_ref"] for row in rows} == {"TXN-A", "TXN-B"}
    assert all(row["status"] == "CAPTURED" for row in rows)
    assert all(row["amount_minor"] == 150000 for row in rows)
    assert all(row["currency"] == "INR" for row in rows)


def test_provider_outcome_and_credit_are_separate_events(client) -> None:
    create = client.post(
        "/v1/refunds",
        headers={**DISPATCHER, "Idempotency-Key": "refund-demo-1"},
        json=REFUND_BODY,
    )
    assert create.status_code == 202
    assert create.json()["status"] == "PENDING"

    missing_credit = client.get("/v1/credits/refund-demo-1", headers=VERIFIER)
    assert missing_credit.status_code == 404

    confirm = client.post("/v1/admin/refunds/refund-demo-1/confirm", headers=ADMIN)
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "PROVIDER_CONFIRMED"

    still_missing = client.get("/v1/credits/refund-demo-1", headers=VERIFIER)
    assert still_missing.status_code == 404

    credit = client.post("/v1/admin/credits/refund-demo-1/confirm", headers=ADMIN)
    assert credit.status_code == 200
    assert credit.json() == {
        "provider_ref": "refund-demo-1",
        "confirmed": True,
        "observed_at": "2026-11-13T12:00:00Z",
    }
    fetched = client.get("/v1/credits/refund-demo-1", headers=VERIFIER)
    assert fetched.status_code == 200
    assert fetched.json()["confirmed"] is True

    events = client.get("/v1/admin/events", headers=ADMIN).json()["events"]
    types = [event["type"] for event in events]
    assert "REFUND_STATUS" in types
    assert "CREDIT_STATUS" in types


def test_idempotent_refund_one_side_effect_and_timeout_recovery(client) -> None:
    client.put(
        "/v1/admin/faults",
        headers=ADMIN,
        json={"timeout_after_accept": True},
    )

    first = client.post(
        "/v1/refunds",
        headers={**DISPATCHER, "Idempotency-Key": "refund-demo-1"},
        json=REFUND_BODY,
    )
    assert first.status_code == 504
    assert first.json()["code"] == "TIMEOUT_AFTER_ACCEPT"

    recovered = client.get("/v1/refunds/refund-demo-1", headers=DISPATCHER)
    assert recovered.status_code == 200
    assert recovered.json()["status"] == "PENDING"
    assert recovered.json()["provider_ref"] == "refund-demo-1"

    stats = client.get("/v1/admin/refunds/refund-demo-1/stats", headers=ADMIN)
    assert stats.status_code == 200
    assert stats.json() == {
        "provider_ref": "refund-demo-1",
        "accept_count": 1,
        "side_effect_count": 1,
        "timeout_count": 1,
    }

    second = client.post(
        "/v1/refunds",
        headers={**DISPATCHER, "Idempotency-Key": "refund-demo-1"},
        json=REFUND_BODY,
    )
    assert second.status_code == 504

    stats_after = client.get("/v1/admin/refunds/refund-demo-1/stats", headers=ADMIN).json()
    assert stats_after["side_effect_count"] == 1
    assert stats_after["accept_count"] == 2
    assert stats_after["timeout_count"] == 2

    listed = client.get(
        "/v1/refunds",
        params={"transaction_ref": "TXN-B"},
        headers=WORKFLOW,
    )
    assert listed.status_code == 200
    assert len(listed.json()["refunds"]) == 1
