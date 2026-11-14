"""Contract: profile read + PATCH /v1/auth/me (no privilege escalation)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.conftest import auth_header, login


def test_me_includes_profile_fields(client: TestClient, demo_password: str) -> None:
    session = login(client, "customer@example.test", demo_password)
    response = client.get("/v1/auth/me", headers=auth_header(session["session_token"]))
    assert response.status_code == 200
    user = response.json()["user"]
    assert user["email"] == "customer@example.test"
    assert user["display_name"] == "Demo Customer"
    assert "preferred_language" in user
    assert isinstance(user["preferred_language"], str)


def test_patch_me_updates_display_name_and_language(client: TestClient, demo_password: str) -> None:
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    response = client.patch(
        "/v1/auth/me",
        headers=headers,
        json={"display_name": "Patched Customer", "preferred_language": "hi"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["user"]["display_name"] == "Patched Customer"
    assert body["user"]["preferred_language"] == "hi"
    assert body["user"]["email"] == "customer@example.test"

    me = client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["display_name"] == "Patched Customer"
    assert me.json()["user"]["preferred_language"] == "hi"


def test_patch_me_rejects_privilege_and_unknown_fields(
    client: TestClient, demo_password: str
) -> None:
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    for payload in (
        {"role": "platform_admin"},
        {"role_id": "supervisor"},
        {"tenant_id": "tenant-other"},
        {"account_type": "staff"},
        {"permissions": ["identity.staff.manage"]},
        {"email": "evil@example.test"},
        {"display_name": "Ok", "unknown_field": "nope"},
    ):
        response = client.patch("/v1/auth/me", headers=headers, json=payload)
        assert response.status_code == 422, payload
        assert response.json()["code"] == "INVALID_INPUT"

    me = client.get("/v1/auth/me", headers=headers)
    assert me.json()["user"]["display_name"] == "Demo Customer"
    assert me.json()["user"]["email"] == "customer@example.test"


def test_patch_me_requires_bearer(client: TestClient) -> None:
    response = client.patch(
        "/v1/auth/me",
        json={"display_name": "No Auth"},
    )
    assert response.status_code == 401
