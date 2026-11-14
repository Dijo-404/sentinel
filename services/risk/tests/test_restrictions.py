"""FLOW-10/11: restriction blocks refund path; clearance never approves money."""

from __future__ import annotations

from tests.conftest import auth


def _seed(client):
    created = client.post(
        "/v1/risk/investigations",
        headers=auth(),
        json={
            "case_id": "case-demo-42",
            "reason_code": "SUSPECTED_DUPLICATE",
            "queue_ref": "FRAUD",
        },
    )
    assert created.status_code == 201
    body = created.json()
    return body["investigation_id"], body["restriction_ids"][0]


def test_active_restriction_blocks_financial_actions(client):
    _investigation_id, _restriction_id = _seed(client)
    response = client.get("/v1/risk/cases/case-demo-42/blocks", headers=auth())
    assert response.status_code == 200
    body = response.json()
    assert body["blocks_financial_actions"] is True
    assert body["financial_approval_granted"] is False


def test_workflow_service_can_lookup_blocks(client):
    _seed(client)
    response = client.get("/v1/risk/cases/case-demo-42/blocks", headers=auth("tok-workflow"))
    assert response.status_code == 200
    body = response.json()
    assert body["blocks_financial_actions"] is True
    assert body["financial_approval_granted"] is False


def test_operator_cannot_lookup_blocks(client):
    _seed(client)
    response = client.get("/v1/risk/cases/case-demo-42/blocks", headers=auth("operator-token"))
    assert response.status_code == 403


def test_record_finding_and_clear_without_money_approval(client, workflow):
    investigation_id, restriction_id = _seed(client)

    finding = client.post(
        f"/v1/risk/investigations/{investigation_id}/findings",
        headers=auth(),
        json={
            "classification": "LEGITIMATE",
            "evidence_ids": ["evidence-payment-b"],
            "notes": "Gateway confirms duplicate capture already reversed by merchant.",
        },
    )
    assert finding.status_code == 201
    assert finding.json()["classification"] == "LEGITIMATE"

    decision = client.post(
        f"/v1/risk/restrictions/{restriction_id}/decision",
        headers=auth(),
        json={
            "decision": "CLEAR",
            "reason": "Legitimate duplicate complaint; resume workflow",
            "evidence_ids": ["evidence-payment-b"],
            "expected_revision": 1,
        },
    )
    assert decision.status_code == 200
    body = decision.json()
    assert body["status"] == "CLEARED"
    assert body["blocks_financial_actions"] is False
    assert body["financial_approval_granted"] is False
    assert body["cleared_by"] == "risk-1"
    assert body["revision"] == 2

    blocks = client.get("/v1/risk/cases/case-demo-42/blocks", headers=auth())
    assert blocks.json()["blocks_financial_actions"] is False

    assert len(workflow.events) == 1
    event = workflow.events[0]
    assert event.event_type == "risk.restriction.cleared"
    assert event.financial_approval_granted is False


def test_maintain_keeps_block(client):
    _investigation_id, restriction_id = _seed(client)
    decision = client.post(
        f"/v1/risk/restrictions/{restriction_id}/decision",
        headers=auth(),
        json={
            "decision": "MAINTAIN",
            "reason": "Still suspicious",
            "expected_revision": 1,
        },
    )
    assert decision.status_code == 200
    assert decision.json()["blocks_financial_actions"] is True
    assert decision.json()["status"] == "MAINTAINED"
    assert decision.json()["financial_approval_granted"] is False


def test_confirm_fraud_keeps_block(client):
    investigation_id, restriction_id = _seed(client)
    client.post(
        f"/v1/risk/investigations/{investigation_id}/findings",
        headers=auth(),
        json={"classification": "CONFIRMED_FRAUD", "evidence_ids": ["ev-1"]},
    )
    decision = client.post(
        f"/v1/risk/restrictions/{restriction_id}/decision",
        headers=auth(),
        json={
            "decision": "CONFIRM_FRAUD",
            "reason": "Confirmed under policy",
            "expected_revision": 1,
        },
    )
    assert decision.status_code == 200
    assert decision.json()["blocks_financial_actions"] is True
    assert decision.json()["financial_approval_granted"] is False


def test_decision_requires_expected_revision(client):
    _investigation_id, restriction_id = _seed(client)
    response = client.post(
        f"/v1/risk/restrictions/{restriction_id}/decision",
        headers=auth(),
        json={"decision": "CLEAR", "reason": "missing revision"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"


def test_stale_expected_revision_conflicts_without_second_resume(client, workflow):
    _investigation_id, restriction_id = _seed(client)
    first = client.post(
        f"/v1/risk/restrictions/{restriction_id}/decision",
        headers=auth(),
        json={
            "decision": "CLEAR",
            "reason": "first clear",
            "expected_revision": 1,
        },
    )
    assert first.status_code == 200
    assert len(workflow.events) == 1

    second = client.post(
        f"/v1/risk/restrictions/{restriction_id}/decision",
        headers=auth(),
        json={
            "decision": "CLEAR",
            "reason": "stale clear",
            "expected_revision": 1,
        },
    )
    assert second.status_code == 409
    assert second.json()["code"] == "CONFLICT"
    assert len(workflow.events) == 1


def test_concurrent_clear_cas_emits_resume_once(service, store, workflow):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from sentinel_risk.application.errors import ConflictError
    from sentinel_risk.domain.types import CreateInvestigationRequest, RestrictionDecisionRequest
    from tests.conftest import RISK_OFFICER

    inv = service.create_investigation(
        RISK_OFFICER,
        CreateInvestigationRequest(case_id="case-demo-42", reason_code="X"),
    )
    restriction_id = inv.restriction_ids[0]

    def _clear() -> str:
        try:
            service.decide_restriction(
                RISK_OFFICER,
                restriction_id,
                RestrictionDecisionRequest(
                    decision="CLEAR",
                    reason="race",
                    expected_revision=1,
                ),
            )
            return "ok"
        except ConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = [fut.result() for fut in as_completed([pool.submit(_clear) for _ in range(8)])]

    assert outcomes.count("ok") == 1
    assert outcomes.count("conflict") == 7
    assert len(workflow.events) == 1
    cleared = store.get_restriction(restriction_id)
    assert cleared is not None
    assert cleared.status == "CLEARED"
