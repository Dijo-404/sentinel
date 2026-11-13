"""Acceptance: missing required evidence blocks submission."""

from __future__ import annotations

from sentinel_merchant_disputes.adapters.peers_fixture import FixtureEvidence
from sentinel_merchant_disputes.domain.types import CreateDisputeRequest
from tests.conftest import OPERATOR, auth


def test_incomplete_packet_blocks_submit(client, service):
    service._evidence = FixtureEvidence(incomplete=True)  # noqa: SLF001
    dispute = service.create(
        OPERATOR,
        CreateDisputeRequest(
            case_id="case-demo-42",
            merchant_ref="merchant-demo",
            reason_code="CHARGEBACK_DUPLICATE",
            deadline_at="2026-11-20T12:30:00Z",
            order_reference="DEMO-ORDER-42",
        ),
    )
    collected = service.collect_packet(OPERATOR, dispute.dispute_id)
    assert collected.status == "EVIDENCE_PENDING"

    response = client.post(f"/v1/disputes/{dispute.dispute_id}/submit", headers=auth())
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "MISSING_REQUIRED_EVIDENCE"
    assert "DELIVERY" in body["message"]


def test_submit_without_packet_blocks(client):
    created = client.post(
        "/v1/disputes",
        headers=auth(),
        json={
            "case_id": "case-demo-42",
            "merchant_ref": "merchant-demo",
            "reason_code": "CHARGEBACK_DUPLICATE",
            "deadline_at": "2026-11-20T12:30:00Z",
            "order_reference": "DEMO-ORDER-42",
        },
    )
    dispute_id = created.json()["dispute_id"]
    response = client.post(f"/v1/disputes/{dispute_id}/submit", headers=auth())
    assert response.status_code == 422
    assert response.json()["code"] == "MISSING_REQUIRED_EVIDENCE"
