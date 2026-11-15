"""Admin tenants / teams / security / roles / audit projections."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.conftest import auth_header, login


def test_admin_list_roles(client: TestClient, demo_password: str) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    response = client.get("/v1/admin/roles", headers=auth_header(admin["session_token"]))
    assert response.status_code == 200
    body = response.json()
    assert "platform_admin" in body["human_roles"]
    assert "operator" in body["staff_invitable_roles"]
    assert "workflow" in body["service_roles"]


def test_admin_list_audit_events(client: TestClient, demo_password: str) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    response = client.get("/v1/admin/audit-events", headers=auth_header(admin["session_token"]))
    assert response.status_code == 200
    assert "events" in response.json()
    assert isinstance(response.json()["events"], list)


def test_admin_list_tenants_includes_demo(client: TestClient, demo_password: str) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    response = client.get("/v1/admin/tenants", headers=auth_header(admin["session_token"]))
    assert response.status_code == 200
    tenants = response.json()["tenants"]
    assert tenants
    by_id = {t["tenant_id"]: t for t in tenants}
    assert "tenant-demo" in by_id
    assert by_id["tenant-demo"]["status"]
    assert "tenant_id" in by_id["tenant-demo"]


def test_admin_list_teams_from_assignments(client: TestClient, demo_password: str) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    response = client.get("/v1/admin/teams", headers=auth_header(admin["session_token"]))
    assert response.status_code == 200
    teams = response.json()["teams"]
    assert teams
    by_id = {t["team_id"]: t for t in teams}
    assert "payments-support" in by_id
    row = by_id["payments-support"]
    assert row["name"]
    assert row["member_count"] >= 1


def test_admin_security_counts(client: TestClient, demo_password: str) -> None:
    admin = login(client, "admin@example.test", demo_password, requested_role="platform_admin")
    # Login creates ≥1 active session for admin
    response = client.get("/v1/admin/security", headers=auth_header(admin["session_token"]))
    assert response.status_code == 200
    body = response.json()
    assert body["active_sessions"] >= 1
    assert isinstance(body["mfa_verified_sessions"], int)
    assert isinstance(body["suspended_users"], int)
    assert body["updated_at"]


def test_admin_projections_require_platform_admin(client: TestClient, demo_password: str) -> None:
    op = login(client, "operator@example.test", demo_password, requested_role="operator")
    headers = auth_header(op["session_token"])
    for path in ("/v1/admin/tenants", "/v1/admin/teams", "/v1/admin/security"):
        assert client.get(path, headers=headers).status_code == 403
