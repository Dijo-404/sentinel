"""AUTH-09 / AUTH-10 — merchant subroles never become money or platform authority."""

from __future__ import annotations

import pytest
from tests.conftest import OPERATOR

from sentinel_merchant_teams.application.errors import (
    FinancialAuthorityDenied,
    ValidationError,
)
from sentinel_merchant_teams.domain.roles import normalize_roles


def test_auth_09_merchant_approver_cannot_authorize_ledger(service, client, auth_headers):
    """AUTH-09: Merchant approver attempts ledger approval → denied."""
    created = service.create(
        OPERATOR,
        merchant_ref="merchant-demo-1",
        display_name="Merchant Approver",
        roles=["approver"],
        approval_limit_minor=9_999_999,
        currency="INR",
        staff_id="staff-approver-auth09",
    )
    assert created.roles == ("approver",)

    with pytest.raises(FinancialAuthorityDenied) as exc:
        service.authorize_money(
            OPERATOR,
            "staff-approver-auth09",
            amount_minor=1,
            currency="INR",
        )
    assert exc.value.code == "FINANCIAL_AUTHORITY_DENIED"

    advisory = service.advisory_check(
        OPERATOR,
        "staff-approver-auth09",
        amount_minor=100,
        currency="INR",
    )
    assert advisory.within_advisory_limit is True
    assert advisory.authorizes_ledger_or_provider is False
    assert advisory.approval_id is None
    assert advisory.reservation_id is None

    denied = client.post(
        "/v1/staff/staff-approver-auth09/authorize",
        headers=auth_headers,
        json={"amount_minor": 100, "currency": "INR"},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "FINANCIAL_AUTHORITY_DENIED"


def test_auth_10_merchant_admin_cannot_grant_platform_roles(service, client, auth_headers):
    """AUTH-10: Merchant admin attempts platform staff grant → denied."""
    admin = service.create(
        OPERATOR,
        merchant_ref="merchant-demo-1",
        display_name="Merchant Admin",
        roles=["admin"],
        staff_id="staff-admin-auth10",
    )
    assert admin.roles == ("admin",)

    with pytest.raises(ValidationError, match="platform role grants"):
        service.create(
            OPERATOR,
            merchant_ref="merchant-demo-1",
            display_name="Escalated",
            roles=["platform_admin"],
            staff_id="staff-platform-attempt",
        )

    with pytest.raises(ValidationError, match="platform role grants"):
        service.update(OPERATOR, "staff-admin-auth10", roles=["supervisor"])

    with pytest.raises(ValidationError, match="platform role grants"):
        service.update(OPERATOR, "staff-admin-auth10", roles=["risk_officer"])

    with pytest.raises(ValueError, match="platform role grants"):
        normalize_roles(["platform:operator"])

    # Local merchant subroles remain allowed.
    ok = service.update(OPERATOR, "staff-admin-auth10", roles=["admin", "viewer"])
    assert ok.roles == ("admin", "viewer")

    http_denied = client.patch(
        "/v1/staff/staff-admin-auth10",
        headers=auth_headers,
        json={"roles": ["platform_admin"]},
    )
    assert http_denied.status_code == 422
    assert "platform role" in http_denied.json()["message"]
