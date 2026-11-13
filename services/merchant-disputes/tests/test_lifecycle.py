"""Acceptance: OPEN → EVIDENCE_PENDING → SUBMITTED → terminal outcomes."""

from __future__ import annotations

from sentinel_merchant_disputes.domain.types import CreateDisputeRequest
from tests.conftest import OPERATOR, auth


def _create(client, **extra):
    body = {
        "case_id": "case-demo-42",
        "merchant_ref": "merchant-demo",
        "reason_code": "CHARGEBACK_DUPLICATE",
        "deadline_at": "2026-11-20T12:30:00Z",
        "order_reference": "DEMO-ORDER-42",
        **extra,
    }
    return client.post("/v1/disputes", headers=auth(), json=body)


def test_full_lifecycle_won(client):
    created = _create(client)
    assert created.status_code == 201
    dispute = created.json()
    assert dispute["status"] == "OPEN"
    dispute_id = dispute["dispute_id"]

    packet = client.post(f"/v1/disputes/{dispute_id}/packets", headers=auth())
    assert packet.status_code == 200
    assert packet.json()["status"] == "EVIDENCE_PENDING"
    assert len(packet.json()["evidence_packet_ids"]) == 1

    submitted = client.post(f"/v1/disputes/{dispute_id}/submit", headers=auth())
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "SUBMITTED"

    won = client.post(
        f"/v1/disputes/{dispute_id}/resolve",
        headers=auth(),
        json={"outcome": "WON"},
    )
    assert won.status_code == 200
    assert won.json()["status"] == "WON"


def test_withdraw_from_open(client, service):
    open_dispute = service.create(
        OPERATOR,
        CreateDisputeRequest(
            case_id="case-demo-42",
            merchant_ref="merchant-demo",
            reason_code="FRAUD_CLAIM",
            deadline_at="2026-11-20T12:30:00Z",
            order_reference="DEMO-ORDER-42",
        ),
    )
    withdrawn = client.post(
        f"/v1/disputes/{open_dispute.dispute_id}/resolve",
        headers=auth(),
        json={"outcome": "WITHDRAWN"},
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "WITHDRAWN"


def test_lifecycle_lost(client):
    created = _create(client)
    dispute_id = created.json()["dispute_id"]
    client.post(f"/v1/disputes/{dispute_id}/packets", headers=auth())
    client.post(f"/v1/disputes/{dispute_id}/submit", headers=auth())
    lost = client.post(
        f"/v1/disputes/{dispute_id}/resolve",
        headers=auth(),
        json={"outcome": "LOST"},
    )
    assert lost.json()["status"] == "LOST"


def test_capabilities_fixture_mode(client):
    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["component"] == "merchant-disputes"
    assert body["mode"] == "fixture"
    assert body["contract_version"] == "sentinel.task-contracts.v1"
