"""Unauthorized tenant/merchant scope fails closed."""

from __future__ import annotations

import pytest
from tests.conftest import OPERATOR, OUTSIDER

from sentinel_merchant_teams.application.errors import NotFoundError, UnauthorizedError
from sentinel_merchant_teams.domain.types import Principal

OTHER_MERCHANT = Principal(
    principal_id="op-2",
    tenant_id="tenant-demo",
    roles=("operator",),
    subject_refs=("merchant-demo-2",),
    case_ids=("case-demo-42",),
)


def test_outsider_cannot_create_or_read(service):
    created = service.create(
        OPERATOR,
        merchant_ref="merchant-demo-1",
        display_name="Ada",
        roles=["viewer"],
        staff_id="staff-scoped",
    )
    assert created.staff_id == "staff-scoped"

    with pytest.raises(UnauthorizedError):
        service.create(
            OUTSIDER,
            merchant_ref="merchant-demo-1",
            display_name="Eve",
            roles=["viewer"],
        )

    # Cross-tenant reads fail closed without leaking foreign-tenant existence.
    with pytest.raises(NotFoundError):
        service.get(OUTSIDER, "staff-scoped")

    with pytest.raises(UnauthorizedError):
        service.list_staff(OUTSIDER, "merchant-demo-1")

    with pytest.raises(UnauthorizedError):
        service.get(OTHER_MERCHANT, "staff-scoped")


def test_http_wrong_token_403(client):
    response = client.post(
        "/v1/staff",
        headers={"Authorization": "Bearer outsider-token"},
        json={
            "merchant_ref": "merchant-demo-1",
            "display_name": "Eve",
            "roles": ["viewer"],
        },
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_missing_bearer_403(client):
    response = client.get("/v1/staff", params={"merchant_ref": "merchant-demo-1"})
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
