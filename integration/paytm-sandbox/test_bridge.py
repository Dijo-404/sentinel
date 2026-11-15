"""Local bridge tests (no live Paytm calls)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from provider_bridge import create_app


class _FakeClient:
    settings = type("S", (), {"mid": "wkyQgn37386655602538"})()

    def __init__(self, body: dict):
        self._body = body

    def transaction_status(self, order_id: str):
        payload = dict(self._body)
        payload.setdefault("orderId", order_id)
        payload.setdefault("mid", self.settings.mid)
        return payload, b"{}"


def test_bridge_maps_success_payment():
    body = {
        "resultInfo": {"resultStatus": "TXN_SUCCESS", "resultCode": "01"},
        "txnId": "TXN-LIVE-1",
        "txnAmount": "10.00",
        "_signature_verified": True,
        "_signature_present": True,
    }
    client = TestClient(create_app(_FakeClient(body)))
    headers = {"Authorization": "Bearer tok-workflow"}
    payments = client.get("/v1/transactions", params={"order_reference": "ORD-1"}, headers=headers)
    assert payments.status_code == 200
    item = payments.json()["payments"][0]
    assert item["status"] == "CAPTURED"
    assert item["amount_minor"] == 1000
    assert item["merchant_ref"] == "merchant-paytm-staging"
    order = client.get("/v1/orders/ORD-1", headers=headers)
    assert order.json()["paid"] is True
    assert order.json()["fulfilled_order_count"] == 0


def test_bridge_missing_order_returns_empty_payments():
    body = {
        "resultInfo": {
            "resultStatus": "TXN_FAILURE",
            "resultCode": "334",
            "resultMsg": "Invalid Order Id.",
        },
        "_signature_verified": True,
        "_signature_present": True,
    }
    client = TestClient(create_app(_FakeClient(body)))
    headers = {"Authorization": "Bearer tok-workflow"}
    payments = client.get(
        "/v1/transactions", params={"order_reference": "MISSING"}, headers=headers
    )
    assert payments.json() == {"payments": []}


def test_bridge_rejects_bad_token():
    client = TestClient(create_app(_FakeClient({"_signature_verified": True})))
    response = client.get(
        "/v1/transactions",
        params={"order_reference": "X"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 403
