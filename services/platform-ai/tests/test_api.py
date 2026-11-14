"""HTTP API: config + run metadata only (no money fields)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.conftest import MONEY_KEYS


def _assert_no_money_fields(payload: object) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in MONEY_KEYS, f"money field leaked: {key}"
            _assert_no_money_fields(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_money_fields(item)


def test_health_ready_capabilities(client: TestClient):
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready["status"] == "ready"
    assert ready["mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps["contract_version"] == "sentinel.task-contracts.v1"
    assert caps["component"] == "platform-ai"
    assert caps["mode"] == "fixture"
    assert caps["money_authority"] is False


def test_get_config_returns_models_kill_switch_updated_at(
    client: TestClient, admin_headers: dict[str, str]
):
    response = client.get("/v1/config", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "models" in body
    assert isinstance(body["models"], list)
    assert len(body["models"]) >= 1
    assert body["models"][0]["model_id"] == "model-sandbox-1"
    assert isinstance(body["kill_switch"], bool)
    assert body["kill_switch"] is False
    assert body["updated_at"].endswith("Z")
    _assert_no_money_fields(body)


def test_get_runs_returns_metadata_only(client: TestClient, admin_headers: dict[str, str]):
    response = client.get("/v1/runs", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "runs" in body
    assert len(body["runs"]) >= 1
    run = body["runs"][0]
    assert run["run_id"] == "run-demo-1"
    assert run["model_id"] == "model-sandbox-1"
    assert run["status"] == "SUCCEEDED"
    assert run["started_at"].endswith("Z")
    assert set(run) == {"run_id", "model_id", "status", "started_at"}
    _assert_no_money_fields(body)


def test_config_and_runs_require_bearer(client: TestClient):
    assert client.get("/v1/config").status_code == 403
    assert client.get("/v1/runs").status_code == 403


def test_operator_denied_admin_surfaces(client: TestClient):
    headers = {"Authorization": "Bearer operator-token"}
    assert client.get("/v1/config", headers=headers).status_code == 403
    assert client.get("/v1/runs", headers=headers).status_code == 403
