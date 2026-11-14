"""HTTP: health, capabilities, activity feed, auth."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from tests.conftest import auth, sample_item


def test_health_ready_capabilities(client: TestClient):
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready["status"] == "ready"
    assert ready["mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps["contract_version"] == "sentinel.task-contracts.v1"
    assert caps["component"] == "ops-activity"
    assert caps["mode"] == "fixture"
    assert caps["port"] == "ops-activity.v1"
    assert caps["financial_authority"] is False


def test_activity_empty(client: TestClient):
    response = client.get("/v1/activity", headers=auth())
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_activity_newest_first_and_cap_50(client: TestClient, store):
    base = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
    for i in range(55):
        store.put(
            sample_item(
                activity_id=f"act-{i:03d}",
                occurred_at=(base + timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                summary=f"Event {i}",
                case_id=None if i % 2 else f"case-{i}",
            )
        )
    response = client.get("/v1/activity", headers=auth())
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 50
    occurred = [row["occurred_at"] for row in items]
    assert occurred == sorted(occurred, reverse=True)
    newest = items[0]
    assert newest["activity_id"] == "act-054"
    assert newest["case_id"] == "case-54"
    # Odd index omits case_id on the wire.
    assert "case_id" not in next(i for i in items if i["activity_id"] == "act-053")


def test_activity_tenant_scoped(client: TestClient, store):
    store.put(sample_item(activity_id="act-demo"))
    store.put(
        sample_item(
            activity_id="act-other",
            tenant_id="tenant-other",
            summary="Other tenant",
        )
    )
    demo = client.get("/v1/activity", headers=auth("operator-token"))
    assert [i["activity_id"] for i in demo.json()["items"]] == ["act-demo"]
    other = client.get("/v1/activity", headers=auth("other-tenant-token"))
    assert [i["activity_id"] for i in other.json()["items"]] == ["act-other"]


def test_activity_requires_bearer(client: TestClient):
    response = client.get("/v1/activity")
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_activity_rejects_customer_role(client: TestClient, store):
    store.put(sample_item())
    response = client.get("/v1/activity", headers=auth("customer-token"))
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_activity_wire_shape(client: TestClient, store):
    store.put(sample_item())
    body = client.get("/v1/activity", headers=auth()).json()
    item = body["items"][0]
    assert item == {
        "activity_id": "act-1",
        "kind": "case.opened",
        "summary": "Case case-demo-42 opened",
        "occurred_at": "2026-11-14T12:00:00Z",
        "case_id": "case-demo-42",
    }
