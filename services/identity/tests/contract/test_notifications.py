"""Contract: GET /v1/auth/notifications + POST .../{id}/read."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.conftest import auth_header, login


def test_list_notifications_seeded_for_customer(client: TestClient, demo_password: str) -> None:
    session = login(client, "customer@example.test", demo_password)
    response = client.get(
        "/v1/auth/notifications",
        headers=auth_header(session["session_token"]),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "notifications" in body
    rows = body["notifications"]
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert len(rows) <= 50
    for row in rows:
        assert set(row.keys()) == {
            "notification_id",
            "title",
            "body",
            "created_at",
            "read_at",
        }
        assert isinstance(row["notification_id"], str)
        assert isinstance(row["title"], str)
        assert isinstance(row["body"], str)
        assert isinstance(row["created_at"], str)
        assert row["read_at"] is None or isinstance(row["read_at"], str)
    created = [r["created_at"] for r in rows]
    assert created == sorted(created, reverse=True)


def test_mark_notification_read(client: TestClient, demo_password: str) -> None:
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    listed = client.get("/v1/auth/notifications", headers=headers)
    assert listed.status_code == 200
    rows = listed.json()["notifications"]
    assert rows
    unread = next((r for r in rows if r["read_at"] is None), rows[0])
    nid = unread["notification_id"]

    response = client.post(f"/v1/auth/notifications/{nid}/read", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["notification_id"] == nid
    assert isinstance(body["read_at"], str)

    again = client.get("/v1/auth/notifications", headers=headers)
    assert again.status_code == 200
    matched = next(r for r in again.json()["notifications"] if r["notification_id"] == nid)
    assert matched["read_at"] == body["read_at"]


def test_mark_read_other_user_notification_404(client: TestClient, demo_password: str) -> None:
    customer = login(client, "customer@example.test", demo_password)
    listed = client.get(
        "/v1/auth/notifications",
        headers=auth_header(customer["session_token"]),
    )
    nid = listed.json()["notifications"][0]["notification_id"]

    merchant = login(client, "merchant@example.test", demo_password)
    response = client.post(
        f"/v1/auth/notifications/{nid}/read",
        headers=auth_header(merchant["session_token"]),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_notifications_require_bearer(client: TestClient) -> None:
    assert client.get("/v1/auth/notifications").status_code == 401
    assert (
        client.post("/v1/auth/notifications/11111111-1111-1111-1111-111111111301/read").status_code
        == 401
    )
