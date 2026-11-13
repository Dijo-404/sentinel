"""HTTP API: metrics, auth scope, capabilities, read-only."""

from __future__ import annotations

from fastapi.testclient import TestClient

from constants import WINDOW


def test_health_ready_capabilities(client: TestClient):
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready["status"] == "ready"
    assert ready["mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps["contract_version"] == "sentinel.task-contracts.v1"
    assert caps["component"] == "merchant-analytics"
    assert caps["mode"] == "fixture"


def test_metrics_deterministic(client: TestClient, metrics_url: str, expected_metrics: dict):
    response = client.get(
        metrics_url,
        params=WINDOW,
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 200
    assert response.json() == expected_metrics


def test_unauthorized_missing_token(client: TestClient, metrics_url: str):
    response = client.get(metrics_url, params=WINDOW)
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_unauthorized_wrong_merchant_scope(client: TestClient, metrics_url: str):
    response = client.get(
        metrics_url,
        params=WINDOW,
        headers={"Authorization": "Bearer other-merchant-token"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "FORBIDDEN"
    # No existence leak via distinct codes.
    assert "not found" not in body["message"].lower()


def test_unauthorized_customer_role(client: TestClient, metrics_url: str):
    response = client.get(
        metrics_url,
        params=WINDOW,
        headers={"Authorization": "Bearer customer-token"},
    )
    assert response.status_code == 403


def test_missing_window_params(client: TestClient, metrics_url: str):
    response = client.get(
        metrics_url,
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"


def test_metrics_reject_mutations(client: TestClient, metrics_url: str):
    headers = {"Authorization": "Bearer operator-token"}
    for method in ("post", "put", "patch"):
        response = getattr(client, method)(
            metrics_url,
            headers=headers,
            json={"unresolved_minor": 1},
        )
        assert response.status_code == 405, method
        assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    response = client.delete(metrics_url, headers=headers)
    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
