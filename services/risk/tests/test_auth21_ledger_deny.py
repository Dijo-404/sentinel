"""AUTH-21: risk officer cannot approve ledger refunds."""

from __future__ import annotations

import pytest

from sentinel_risk.application.errors import LedgerApprovalForbiddenError
from tests.conftest import RISK_OFFICER, auth
from tests.stubs.ledger import deny as ledger_deny


def test_http_ops_decision_denied(client):
    response = client.post(
        "/v1/ops/actions/action-refund-1/decisions",
        headers=auth(),
        json={"decision": "APPROVE", "amount_minor": 150000, "currency": "INR"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "LEDGER_APPROVAL_FORBIDDEN"


def test_http_ledger_approvals_denied(client):
    response = client.post(
        "/v1/ledger/approvals",
        headers=auth(),
        json={"action_id": "action-refund-1", "decision": "APPROVE"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "LEDGER_APPROVAL_FORBIDDEN"


def test_service_deny_ledger_approval(service):
    with pytest.raises(LedgerApprovalForbiddenError):
        service.deny_ledger_approval(RISK_OFFICER, action_id="action-refund-1")


def test_local_ledger_stub_denies():
    with pytest.raises(LedgerApprovalForbiddenError):
        ledger_deny.approve(action_id="action-refund-1", decision="APPROVE")


def test_capabilities_declare_no_financial_authority(client):
    assert client.get("/v1/capabilities").json()["financial_authority"] is False
