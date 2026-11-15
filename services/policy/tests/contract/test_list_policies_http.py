"""HTTP contract: GET /v1/policies lists seeded versioned artifacts."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_policies_includes_demo_policy_v1(
    client: TestClient, platform_admin_auth: dict[str, str]
) -> None:
    response = client.get("/v1/policies", headers=platform_admin_auth)
    assert response.status_code == 200
    body = response.json()
    assert "policies" in body
    assert isinstance(body["policies"], list)
    assert len(body["policies"]) >= 1
    demo = next(p for p in body["policies"] if p["policy_id"] == "demo-policy-v1")
    assert demo["version"] == "demo-policy-v1"
    assert demo["status"] == "active"
    assert demo["updated_at"].endswith("Z")
    assert set(demo) == {"policy_id", "version", "status", "updated_at"}


def test_list_policies_allows_workflow_token(
    client: TestClient, workflow_auth: dict[str, str]
) -> None:
    response = client.get("/v1/policies", headers=workflow_auth)
    assert response.status_code == 200
    assert any(p["policy_id"] == "demo-policy-v1" for p in response.json()["policies"])


def test_list_policies_allows_sandbox_admin(
    client: TestClient, sandbox_admin_auth: dict[str, str]
) -> None:
    response = client.get("/v1/policies", headers=sandbox_admin_auth)
    assert response.status_code == 200
    assert any(p["policy_id"] == "demo-policy-v1" for p in response.json()["policies"])


def test_list_policies_missing_auth_unauthorized(client: TestClient) -> None:
    response = client.get("/v1/policies")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_list_policies_operator_forbidden(client: TestClient) -> None:
    response = client.get(
        "/v1/policies",
        headers={"Authorization": "Bearer operator-demo-token"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
