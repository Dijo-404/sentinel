"""Acceptance: deadline tracking and overdue submission gate."""

from __future__ import annotations

from sentinel_merchant_disputes.domain.types import CreateDisputeRequest
from tests.conftest import OPERATOR, auth


def test_deadline_not_overdue_then_overdue(client, service, clock):
    dispute = service.create(
        OPERATOR,
        CreateDisputeRequest(
            case_id="case-demo-42",
            merchant_ref="merchant-demo",
            reason_code="CHARGEBACK_DUPLICATE",
            deadline_at="2026-11-13T13:00:00Z",
            order_reference="DEMO-ORDER-42",
        ),
    )
    view = client.get(f"/v1/disputes/{dispute.dispute_id}/deadline", headers=auth())
    assert view.status_code == 200
    body = view.json()
    assert body["deadline_at"] == "2026-11-13T13:00:00Z"
    assert body["overdue"] is False

    clock.advance(hours=1)
    overdue = client.get(f"/v1/disputes/{dispute.dispute_id}/deadline", headers=auth())
    assert overdue.json()["overdue"] is True


def test_submit_after_deadline_blocked(client, service, clock):
    dispute = service.create(
        OPERATOR,
        CreateDisputeRequest(
            case_id="case-demo-42",
            merchant_ref="merchant-demo",
            reason_code="CHARGEBACK_DUPLICATE",
            deadline_at="2026-11-13T12:45:00Z",
            order_reference="DEMO-ORDER-42",
        ),
    )
    service.collect_packet(OPERATOR, dispute.dispute_id)
    clock.advance(minutes=30)
    response = client.post(f"/v1/disputes/{dispute.dispute_id}/submit", headers=auth())
    assert response.status_code == 422
    assert response.json()["code"] == "DEADLINE_PASSED"
