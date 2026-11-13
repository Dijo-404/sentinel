"""Assessment distinguishes pending / provider-confirmed / credit-confirmed."""

from __future__ import annotations

from tests.conftest import ACTION_ID, PROVIDER_REF, auth_header

from sentinel_verifier.domain.types import Credit, Refund


def test_pending_refund_is_waiting_not_credit(memory_client, tokens, verification_request):
    response = memory_client.post(
        "/v1/assessments",
        headers=auth_header(tokens["workflow"]),
        json=verification_request,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "WAITING"
    assert "REFUND_PENDING" in body["reason_codes"]
    assert "CREDIT_NOT_CONFIRMED" in body["reason_codes"]
    refund_ev = next(e for e in body["evidence"] if e["facts"]["kind"] == "REFUND")
    assert refund_ev["verification_status"] == "UNVERIFIED"
    assert memory_client.ledger.get_action(ACTION_ID)["status"] == "PENDING"
    assert memory_client.ledger.reservation_held(ACTION_ID)
    assert memory_client.case_api.results == []


def test_provider_confirmed_without_credit_stays_waiting(
    memory_client, tokens, verification_request
):
    memory_client.provider.seed_refund(
        Refund(
            action_id=ACTION_ID,
            provider_ref=PROVIDER_REF,
            transaction_ref="TXN-B",
            amount_minor=150000,
            currency="INR",
            status="PROVIDER_CONFIRMED",
        )
    )
    response = memory_client.post(
        "/v1/assessments",
        headers=auth_header(tokens["workflow"]),
        json=verification_request,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "WAITING"
    assert "PROVIDER_CONFIRMED" in body["reason_codes"]
    assert "CREDIT_NOT_CONFIRMED" in body["reason_codes"]
    refund_ev = next(e for e in body["evidence"] if e["facts"]["kind"] == "REFUND")
    assert refund_ev["verification_status"] == "VERIFIED"
    assert memory_client.ledger.get_action(ACTION_ID)["status"] == "PROVIDER_CONFIRMED"
    assert memory_client.ledger.reservation_held(ACTION_ID)
    assert memory_client.case_api.results == []


def test_credit_confirmed_verifies_and_posts_ledger_then_case(
    memory_client, tokens, verification_request, credit_confirmed
):
    del credit_confirmed
    response = memory_client.post(
        "/v1/assessments",
        headers=auth_header(tokens["workflow"]),
        json=verification_request,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "VERIFIED"
    assert "CREDIT_CONFIRMED" in body["reason_codes"]
    assert memory_client.ledger.get_action(ACTION_ID)["status"] == "CREDIT_CONFIRMED"
    assert not memory_client.ledger.reservation_held(ACTION_ID)
    assert len(memory_client.case_api.results) == 1
    announced = memory_client.case_api.results[0]
    assert announced["status"] == "VERIFIED_RESOLVED"
    assert announced["assessment_id"] == body["assessment_id"]

    fetched = memory_client.get(
        f"/v1/assessments/{body['assessment_id']}",
        headers=auth_header(tokens["verifier"]),
    )
    assert fetched.status_code == 200
    assert fetched.json()["assessment_id"] == body["assessment_id"]


def test_unknown_outcome_retains_reservation(memory_client, tokens, verification_request):
    memory_client.ledger.seed_action(
        action_id=ACTION_ID, provider_ref=PROVIDER_REF, status="OUTCOME_UNKNOWN"
    )
    # No refund visible yet.
    memory_client.provider.refunds.clear()
    response = memory_client.post(
        "/v1/assessments",
        headers=auth_header(tokens["workflow"]),
        json=verification_request,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "WAITING"
    assert "REFUND_NOT_VISIBLE" in response.json()["reason_codes"]
    assert memory_client.ledger.reservation_held(ACTION_ID)


def test_conflicting_evidence_escalates_assessment(memory_client, tokens, verification_request):
    memory_client.evidence.seed(
        verification_request["case_id"],
        [
            {
                "evidence_id": "evidence-conflict",
                "case_id": verification_request["case_id"],
                "source": "fixture",
                "subject_ref": "subject-demo-1",
                "observed_at": "2026-11-13T12:00:00Z",
                "expires_at": "2026-11-13T13:00:00Z",
                "digest": "abc",
                "verification_status": "CONFLICTING",
                "facts": {
                    "kind": "PAYMENT",
                    "payment": {
                        "transaction_ref": "TXN-B",
                        "order_reference": "ORD-1",
                        "subject_ref": "subject-demo-1",
                        "status": "CAPTURED",
                        "amount_minor": 150000,
                        "currency": "INR",
                    },
                },
            }
        ],
    )
    response = memory_client.post(
        "/v1/assessments",
        headers=auth_header(tokens["workflow"]),
        json=verification_request,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CONFLICT"


def test_operator_cannot_create_assessment(memory_client, tokens, verification_request):
    response = memory_client.post(
        "/v1/assessments",
        headers=auth_header(tokens["operator"]),
        json=verification_request,
    )
    assert response.status_code == 403


def test_credit_without_prior_provider_confirm_path(memory_client, tokens, verification_request):
    """Credit evidence alone never skips provider confirmation semantics."""
    memory_client.provider.seed_credit(
        Credit(provider_ref=PROVIDER_REF, confirmed=True, observed_at="2026-11-13T12:00:00Z")
    )
    # Refund still PENDING — credit must not close.
    response = memory_client.post(
        "/v1/assessments",
        headers=auth_header(tokens["workflow"]),
        json=verification_request,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "WAITING"
    assert memory_client.ledger.get_action(ACTION_ID)["status"] == "PENDING"
