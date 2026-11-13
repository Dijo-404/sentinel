"""Acceptance: list/filter/assign/note/escalate; escalated != resolved; scope fail-closed."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_synthetic_kinds(client: TestClient, merchant_auth: dict[str, str]) -> None:
    response = client.get(
        "/v1/exceptions",
        params={"merchant_ref": "merchant-demo-1"},
        headers=merchant_auth,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    kinds = {item["kind"] for item in items}
    assert kinds == {"PAID_UNFULFILLED", "UNMATCHED_PAYMENT", "PENDING_REFUND"}
    assert all(isinstance(item["amount_minor"], int) for item in items)
    assert all(item["merchant_ref"] == "merchant-demo-1" for item in items)


def test_filter_by_kind_and_status(client: TestClient, merchant_auth: dict[str, str]) -> None:
    response = client.get(
        "/v1/exceptions",
        params={
            "merchant_ref": "merchant-demo-1",
            "kind": "PENDING_REFUND",
            "status": "OPEN",
        },
        headers=merchant_auth,
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["item_id"] == "exc-pending-refund-1"


def test_assign_and_note(client: TestClient, merchant_auth: dict[str, str]) -> None:
    assigned = client.post(
        "/v1/exceptions/exc-unmatched-1/assign",
        json={"assignee": "ops-rita"},
        headers=merchant_auth,
    )
    assert assigned.status_code == 200
    body = assigned.json()
    assert body["status"] == "ASSIGNED"
    assert body["assignee"] == "ops-rita"

    noted = client.post(
        "/v1/exceptions/exc-unmatched-1/notes",
        json={"note": "waiting on bank advice"},
        headers=merchant_auth,
    )
    assert noted.status_code == 200
    assert noted.json()["notes"] == ["waiting on bank advice"]
    assert noted.json()["status"] == "ASSIGNED"


def test_escalate_is_not_resolved(client: TestClient, merchant_auth: dict[str, str]) -> None:
    response = client.post(
        "/v1/exceptions/exc-paid-unfulfilled-1/escalate",
        json={"reason_code": "MERCHANT_CONFIRMATION_REQUIRED", "owner_queue": "SUPERVISOR"},
        headers=merchant_auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ESCALATED"
    assert body["status"] != "CLOSED"
    assert body["resolved"] is False
    assert body["financial_outcome"] is None


def test_unauthorized_merchant_scope_fails_closed(
    client: TestClient, merchant_auth: dict[str, str]
) -> None:
    response = client.get(
        "/v1/exceptions",
        params={"merchant_ref": "merchant-demo-2"},
        headers=merchant_auth,
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_other_tenant_cannot_see_items(
    client: TestClient, other_tenant_auth: dict[str, str]
) -> None:
    response = client.get(
        "/v1/exceptions",
        params={"merchant_ref": "merchant-other"},
        headers=other_tenant_auth,
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_customer_role_forbidden(client: TestClient, customer_auth: dict[str, str]) -> None:
    response = client.get(
        "/v1/exceptions",
        params={"merchant_ref": "merchant-demo-1"},
        headers=customer_auth,
    )
    assert response.status_code == 403


def test_missing_auth(client: TestClient) -> None:
    response = client.get("/v1/exceptions", params={"merchant_ref": "merchant-demo-1"})
    assert response.status_code == 401
