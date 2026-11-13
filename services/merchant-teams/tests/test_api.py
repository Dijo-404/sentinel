"""HTTP surface for merchant-teams.v1."""

from __future__ import annotations


def test_capabilities_and_health(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz").json()
    assert ready["status"] == "ready"
    assert ready["mode"] == "fixture"
    caps = client.get("/v1/capabilities").json()
    assert caps == {
        "contract_version": "sentinel.task-contracts.v1",
        "component": "merchant-teams",
        "mode": "fixture",
    }


def test_http_crud_timeline(client, auth_headers):
    created = client.post(
        "/v1/staff",
        headers=auth_headers,
        json={
            "merchant_ref": "merchant-demo-1",
            "display_name": "Ada Merchant",
            "roles": ["operator"],
            "staff_id": "staff-api-1",
        },
    )
    assert created.status_code == 201
    assert created.json()["active"] is True

    listed = client.get(
        "/v1/staff",
        headers=auth_headers,
        params={"merchant_ref": "merchant-demo-1"},
    )
    assert listed.status_code == 200
    assert listed.json()["staff"][0]["staff_id"] == "staff-api-1"

    patched = client.patch(
        "/v1/staff/staff-api-1",
        headers=auth_headers,
        json={"roles": ["operator", "approver"], "approval_limit_minor": 1000, "currency": "INR"},
    )
    assert patched.status_code == 200
    assert patched.json()["roles"] == ["operator", "approver"]

    activity = client.get("/v1/staff/staff-api-1/activity", headers=auth_headers)
    assert activity.status_code == 200
    kinds = [event["kind"] for event in activity.json()["events"]]
    assert kinds == ["STAFF_CREATED", "ROLE_ASSIGNED"]

    deactivated = client.post("/v1/staff/staff-api-1/deactivate", headers=auth_headers)
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False


def test_snapshot_fixture_round_trip():
    import json
    from pathlib import Path

    from sentinel_merchant_teams.domain.types import MerchantStaff, StaffActivity

    root = Path(__file__).resolve().parents[1]
    snapshots = json.loads((root / "contracts" / "snapshots.json").read_text())
    staff = MerchantStaff.from_wire(snapshots["MerchantStaff"])
    assert staff.to_wire()["staff_id"] == "staff-demo-1"
    event = StaffActivity(**snapshots["StaffActivity"])
    assert event.to_wire()["kind"] == "STAFF_CREATED"
