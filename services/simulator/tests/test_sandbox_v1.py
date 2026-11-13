from __future__ import annotations

import hashlib
import hmac
import json

from tokens import ADMIN, WORKFLOW


def test_journey_seed_packs_loaded_on_startup(client) -> None:
    pending = client.get("/v1/orders/JOURNEY-PENDING", headers=WORKFLOW)
    assert pending.status_code == 200
    assert pending.json()["paid"] is False
    pay = client.get(
        "/v1/transactions",
        params={"order_reference": "JOURNEY-PENDING"},
        headers=WORKFLOW,
    )
    assert pay.json()["payments"][0]["status"] == "PENDING"
    assert pay.json()["payments"][0]["amount_minor"] == 150000

    mismatch = client.get("/v1/orders/JOURNEY-MISMATCH", headers=WORKFLOW)
    assert mismatch.status_code == 200
    assert mismatch.json()["paid"] is False
    mpay = client.get(
        "/v1/transactions",
        params={"order_reference": "JOURNEY-MISMATCH"},
        headers=WORKFLOW,
    )
    assert mpay.json()["payments"][0]["status"] == "CAPTURED"

    refunds = client.get(
        "/v1/refunds",
        params={"transaction_ref": "TXN-REFUND-PENDING"},
        headers=WORKFLOW,
    )
    assert refunds.status_code == 200
    assert refunds.json()["refunds"][0]["status"] == "PENDING"
    assert refunds.json()["refunds"][0]["provider_ref"] == "refund-pending-1"
    assert refunds.json()["refunds"][0]["amount_minor"] == 150000


def test_fault_schedules_and_aliases(client) -> None:
    applied = client.post(
        "/v1/admin/faults/schedules/timeout-after-accept",
        headers=ADMIN,
    )
    assert applied.status_code == 200
    assert applied.json()["timeout_after_accept"] is True

    client.post("/v1/admin/faults/reset", headers=ADMIN)
    dup = client.post(
        "/v1/admin/faults/schedules/duplicate-webhook",
        headers=ADMIN,
    )
    assert dup.json()["duplicate_events"] is True

    client.put(
        "/v1/admin/faults",
        headers=ADMIN,
        json={"duplicate_webhook": True, "out_of_order": True},
    )
    faults = client.get("/v1/admin/faults", headers=ADMIN).json()
    assert faults["duplicate_events"] is True
    assert faults["out_of_order_credit"] is True


def test_demo_reset_sandbox_tenant_only(client, non_sandbox_client) -> None:
    client.post(
        "/v1/admin/seeds/pending",
        headers=ADMIN,
    )
    # After single-pack load, duplicate hero is gone until reset.
    assert client.get("/v1/orders/DEMO-ORDER-42", headers=WORKFLOW).status_code == 404

    reset = client.post("/v1/admin/demo-reset", headers=ADMIN)
    assert reset.status_code == 200
    body = reset.json()
    assert body["reset"] is True
    assert body["tenant_id"] == "tenant-demo"
    assert body["payment_provider"] == "simulator"
    assert "DEMO-ORDER-42" in body["orders"]
    assert client.get("/v1/orders/DEMO-ORDER-42", headers=WORKFLOW).status_code == 200

    denied = non_sandbox_client.post("/v1/admin/demo-reset", headers=ADMIN)
    assert denied.status_code == 403


def test_signed_webhook_and_settlement_alias(client) -> None:
    emit = client.post(
        "/v1/admin/webhooks/emit",
        headers=ADMIN,
        json={"provider_ref": "refund-pending-1", "type": "REFUND_STATUS"},
    )
    assert emit.status_code == 200
    envelope = emit.json()
    raw = envelope["raw_body"].encode("utf-8")
    expected = hmac.new(
        b"demo-simulator-hmac-key",
        raw,
        hashlib.sha256,
    ).hexdigest()
    assert envelope["signature"] == expected
    assert envelope["headers"]["X-Sentinel-Signature"] == expected
    assert json.loads(envelope["raw_body"])["provider_ref"] == "refund-pending-1"

    # Settlement alias 404 until credit confirmed.
    assert client.get("/v1/settlements/refund-pending-1", headers=WORKFLOW).status_code == 404
