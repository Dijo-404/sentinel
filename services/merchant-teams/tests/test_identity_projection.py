"""Identity-authoritative membership projection (SN-039)."""

from __future__ import annotations

import pytest
from tests.conftest import OPERATOR
from tests.stubs.identity import MALFORMED, UNAUTHORIZED, UNAVAILABLE, VALID

from sentinel_merchant_teams.application.errors import (
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
    ValidationError,
)


def test_identity_stub_modes():
    rows = VALID.list_memberships(
        tenant_id="tenant-demo",
        merchant_ref="merchant-demo-1",
        principal=OPERATOR,
    )
    assert len(rows) == 2
    assert rows[0].subroles == ("approver",)

    with pytest.raises(PeerUnavailableError):
        UNAVAILABLE.list_memberships(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            principal=OPERATOR,
        )
    with pytest.raises(PeerMalformedError):
        MALFORMED.list_memberships(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            principal=OPERATOR,
        )
    with pytest.raises(PeerUnauthorizedError):
        UNAUTHORIZED.list_memberships(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            principal=OPERATOR,
        )


def test_sync_projects_identity_memberships(service):
    projected = service.sync_memberships(OPERATOR, "merchant-demo-1")
    assert [row.staff_id for row in projected] == ["mm-demo-1", "mm-demo-2"]
    assert projected[0].roles == ("approver",)
    assert projected[1].roles == ("admin",)
    assert all(row.active for row in projected)

    listed = service.list_staff(OPERATOR, "merchant-demo-1")
    assert [row.staff_id for row in listed] == ["mm-demo-1", "mm-demo-2"]

    events = service.list_activity(OPERATOR, "mm-demo-1")
    assert events[0].kind == "MEMBERSHIP_PROJECTED"

    again = service.sync_memberships(OPERATOR, "merchant-demo-1")
    assert again[0].staff_id == "mm-demo-1"
    synced = service.list_activity(OPERATOR, "mm-demo-1")
    assert [event.kind for event in synced] == ["MEMBERSHIP_PROJECTED", "MEMBERSHIP_SYNCED"]


def test_sync_fail_closed_when_identity_unavailable(service, identity):
    identity.mode = "unavailable"
    with pytest.raises(PeerUnavailableError):
        service.sync_memberships(OPERATOR, "merchant-demo-1")


def test_sync_rejects_platform_subroles_from_identity(service, identity):
    identity.seed(
        tenant_id="tenant-demo",
        merchant_ref="merchant-demo-1",
        rows=[
            {
                "membership_id": "mm-bad",
                "assignment_id": "asg-bad",
                "user_id": "user-bad",
                "tenant_id": "tenant-demo",
                "merchant_ref": "merchant-demo-1",
                "display_name": "Escalation Attempt",
                "subroles": ["platform_admin"],
                "status": "active",
            }
        ],
    )
    with pytest.raises(ValidationError, match="platform role grants"):
        service.sync_memberships(OPERATOR, "merchant-demo-1")


def test_http_sync_and_team_projection(client, auth_headers):
    synced = client.post(
        "/v1/staff/sync",
        headers=auth_headers,
        json={"merchant_ref": "merchant-demo-1"},
    )
    assert synced.status_code == 200
    body = synced.json()
    assert [row["staff_id"] for row in body["staff"]] == ["mm-demo-1", "mm-demo-2"]

    team = client.get(
        "/v1/merchant/team",
        headers=auth_headers,
        params={"merchant_ref": "merchant-demo-1"},
    )
    assert team.status_code == 200
    assert team.json()["staff"][0]["roles"] == ["approver"]
