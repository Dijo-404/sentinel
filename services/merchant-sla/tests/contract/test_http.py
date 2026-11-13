"""HTTP contract: policies, tasks, overdue, escalate≠done."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from tests.conftest import PRINCIPALS, T0

from sentinel_merchant_sla.adapters.case_api_fixture import FixtureCaseApi
from sentinel_merchant_sla.adapters.clock import FixedClock
from sentinel_merchant_sla.adapters.memory_store import MemorySlaStore
from sentinel_merchant_sla.bootstrap import Settings, build_app
from sentinel_merchant_sla.contracts import CONTRACT_SHA256, CONTRACT_VERSION


def _client(clock: FixedClock | None = None, case_api: FixtureCaseApi | None = None) -> TestClient:
    app = build_app(
        settings=Settings(
            mode="fixture",
            principals_path=PRINCIPALS,
            case_api_base_url="",
            case_api_token="",
        ),
        clock=clock or FixedClock(T0),
        store=MemorySlaStore(),
        case_api=case_api or FixtureCaseApi(behavior="valid"),
    )
    return TestClient(app)


AUTH = {"Authorization": "Bearer merchant-ops-demo-token"}


def test_capabilities_and_health():
    client = _client()
    assert client.get("/healthz").json()["status"] == "ok"
    ready = client.get("/readyz").json()
    assert ready["mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps["contract_version"] == CONTRACT_VERSION
    assert caps["component"] == "merchant-sla"
    assert caps["mode"] == "fixture"
    assert caps["port"] == "merchant-sla.v1"
    assert CONTRACT_SHA256.startswith("0db3ba2b")


def test_policy_task_overdue_follow_up_escalate_complete():
    clock = FixedClock(T0)
    client = _client(clock=clock)

    policy_resp = client.post(
        "/v1/policies",
        headers=AUTH,
        json={
            "tenant_id": "demo-tenant-a",
            "merchant_ref": "merchant-demo-a",
            "respond_within_seconds": 900,
            "resolve_within_seconds": 3600,
        },
    )
    assert policy_resp.status_code == 200
    policy = policy_resp.json()
    assert policy["respond_within_seconds"] == 900

    task_resp = client.post(
        "/v1/tasks",
        headers=AUTH,
        json={
            "case_id": "case-demo-42",
            "policy_id": policy["policy_id"],
            "target": "resolve",
        },
    )
    assert task_resp.status_code == 200
    task = task_resp.json()
    assert task["status"] == "OPEN"
    assert task["overdue"] is False
    assert task["due_at"] == "2026-11-13T11:00:00Z"
    assert "financially_resolved" in task
    assert task["financially_resolved"] is False

    clock.set(datetime(2026, 11, 13, 11, 0, 0, tzinfo=UTC))
    got = client.get(f"/v1/tasks/{task['task_id']}", headers=AUTH).json()
    assert got["overdue"] is True

    follow = client.post(
        f"/v1/tasks/{task['task_id']}/follow-ups",
        headers=AUTH,
        json={"follow_up_at": "2026-11-13T12:30:00Z"},
    ).json()
    assert follow["follow_up_at"] == "2026-11-13T12:30:00Z"

    assigned = client.post(
        f"/v1/tasks/{task['task_id']}/assign",
        headers=AUTH,
        json={"assignee": "op-merchant-demo"},
    ).json()
    assert assigned["assignee"] == "op-merchant-demo"
    assert assigned["status"] == "IN_PROGRESS"

    escalated = client.post(
        f"/v1/tasks/{task['task_id']}/escalate",
        headers=AUTH,
        json={"reason_code": "SLA_BREACH", "owner_queue": "merchant-ops"},
    ).json()
    assert escalated["status"] == "ESCALATED"
    assert escalated["status"] != "DONE"
    assert escalated["case_status"] == "ESCALATED"
    assert escalated["financially_resolved"] is False
    assert escalated["overdue"] is True

    done = client.post(f"/v1/tasks/{task['task_id']}/complete", headers=AUTH).json()
    assert done["status"] == "DONE"
    assert done["overdue"] is False
    assert done["financially_resolved"] is False

    overdue_list = client.get(
        "/v1/tasks",
        headers=AUTH,
        params={"merchant_ref": "merchant-demo-a", "overdue_only": "true"},
    ).json()
    assert overdue_list["tasks"] == []


def test_unauthorized_request():
    client = _client()
    resp = client.post(
        "/v1/policies",
        json={
            "tenant_id": "demo-tenant-a",
            "merchant_ref": "merchant-demo-a",
            "respond_within_seconds": 1,
            "resolve_within_seconds": 2,
        },
    )
    assert resp.status_code == 401
