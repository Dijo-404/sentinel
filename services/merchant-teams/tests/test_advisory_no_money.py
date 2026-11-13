"""Advisory limits never authorize ledger/provider writes."""

from __future__ import annotations

import pytest
from tests.conftest import OPERATOR

from sentinel_merchant_teams.application.errors import FinancialAuthorityDenied
from sentinel_merchant_teams.domain.advisory import (
    check_advisory_limit,
    refuse_financial_authorization,
)
from sentinel_merchant_teams.domain.types import MerchantStaff


def _staff(**overrides):
    base = dict(
        staff_id="staff-demo-1",
        tenant_id="tenant-demo",
        merchant_ref="merchant-demo-1",
        display_name="Ada",
        roles=("approver",),
        active=True,
        approval_limit_minor=50000,
        currency="INR",
    )
    base.update(overrides)
    return MerchantStaff(**base)


def test_advisory_check_never_mints_approval_or_reservation(service):
    service.create(
        OPERATOR,
        merchant_ref="merchant-demo-1",
        display_name="Ada",
        roles=["approver"],
        approval_limit_minor=50000,
        currency="INR",
        staff_id="staff-demo-1",
    )
    result = service.advisory_check(OPERATOR, "staff-demo-1", amount_minor=25000, currency="INR")
    assert result.within_advisory_limit is True
    assert result.advisory is True
    assert result.authorizes_ledger_or_provider is False
    assert result.approval_id is None
    assert result.reservation_id is None

    over = service.advisory_check(OPERATOR, "staff-demo-1", amount_minor=75000, currency="INR")
    assert over.within_advisory_limit is False
    assert over.authorizes_ledger_or_provider is False


def test_domain_refuse_financial_authorization():
    with pytest.raises(PermissionError, match="advisory only"):
        refuse_financial_authorization()


def test_authorize_money_use_case_denied(service):
    service.create(
        OPERATOR,
        merchant_ref="merchant-demo-1",
        display_name="Ada",
        roles=["approver"],
        approval_limit_minor=9_999_999,
        currency="INR",
        staff_id="staff-rich",
    )
    with pytest.raises(FinancialAuthorityDenied) as exc:
        service.authorize_money(OPERATOR, "staff-rich", amount_minor=1, currency="INR")
    assert exc.value.code == "FINANCIAL_AUTHORITY_DENIED"
    wire = check_advisory_limit(_staff(), amount_minor=1, currency="INR").to_wire()
    assert wire["approval_id"] is None
    assert wire["reservation_id"] is None


def test_http_authorize_always_403(client, auth_headers):
    create = client.post(
        "/v1/staff",
        headers=auth_headers,
        json={
            "merchant_ref": "merchant-demo-1",
            "display_name": "Ada",
            "roles": ["approver"],
            "approval_limit_minor": 50000,
            "currency": "INR",
            "staff_id": "staff-http",
        },
    )
    assert create.status_code == 201
    denied = client.post(
        "/v1/staff/staff-http/authorize",
        headers=auth_headers,
        json={"amount_minor": 100, "currency": "INR"},
    )
    assert denied.status_code == 403
    body = denied.json()
    assert body["code"] == "FINANCIAL_AUTHORITY_DENIED"
    assert "approval" not in body
    assert "reservation" not in body

    advisory = client.post(
        "/v1/staff/staff-http/advisory-check",
        headers=auth_headers,
        json={"amount_minor": 100, "currency": "INR"},
    )
    assert advisory.status_code == 200
    payload = advisory.json()
    assert payload["authorizes_ledger_or_provider"] is False
    assert payload["approval_id"] is None
    assert payload["reservation_id"] is None
