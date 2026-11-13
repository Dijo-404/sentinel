"""Deterministic refund rules: eligibility, evidence, approval."""

from __future__ import annotations

import copy

import pytest

from sentinel_policy.application.evaluate import EvaluatePolicy
from sentinel_policy.contracts import PolicyInputError, Principal, parse_policy_request
from sentinel_policy.domain import reason_codes as rc


def _principal(**overrides) -> Principal:
    base = {
        "principal_id": "svc-workflow-demo",
        "tenant_id": "tenant-demo",
        "roles": ("workflow",),
        "subject_refs": ("subject-demo-42",),
        "case_ids": ("case-demo-42",),
    }
    base.update(overrides)
    return Principal(**base)


def test_allow_with_matching_approval(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    req = parse_policy_request(allow_request)
    result = evaluate(_principal(), req)
    assert result.outcome == "ALLOW"
    assert rc.REFUND_APPROVED in result.reason_codes
    assert result.action_digest == (
        "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993"
    )


def test_wrong_tenant_case_denied(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    req = parse_policy_request(allow_request)
    principal = _principal(case_ids=("case-other",), tenant_id="demo-tenant-b")
    result = evaluate(principal, req)
    assert result.outcome == "DENY"
    assert rc.TENANT_SCOPE_DENIED in result.reason_codes


def test_empty_case_ids_denied(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    req = parse_policy_request(allow_request)
    result = evaluate(_principal(case_ids=()), req)
    assert result.outcome == "DENY"
    assert rc.TENANT_SCOPE_DENIED in result.reason_codes


def test_star_case_ids_allows(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    req = parse_policy_request(allow_request)
    result = evaluate(_principal(case_ids=("*",)), req)
    assert result.outcome == "ALLOW"
    assert rc.REFUND_APPROVED in result.reason_codes


def test_wrong_subject_denied(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    req = parse_policy_request(allow_request)
    principal = _principal(subject_refs=("subject-other",))
    result = evaluate(principal, req)
    assert result.outcome == "DENY"
    assert rc.SUBJECT_SCOPE_DENIED in result.reason_codes


@pytest.mark.parametrize(
    ("status", "code"),
    [
        ("PENDING", rc.PAYMENT_PENDING),
        ("FAILED", rc.PAYMENT_FAILED),
    ],
)
def test_pending_or_failed_payment_denied(
    evaluate: EvaluatePolicy,
    allow_request: dict,
    status: str,
    code: str,
) -> None:
    body = copy.deepcopy(allow_request)
    body["evidence"][0]["facts"]["payment"]["status"] = status
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "DENY"
    assert code in result.reason_codes


def test_expired_evidence_needs_evidence(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    body = copy.deepcopy(allow_request)
    body["evidence"][0]["expires_at"] = "2026-11-13T11:00:00Z"
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "NEED_EVIDENCE"
    assert rc.EVIDENCE_EXPIRED in result.reason_codes


def test_fraud_signal_denied(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    body = copy.deepcopy(allow_request)
    body["evidence"].append(
        {
            "evidence_id": "evidence-fraud",
            "case_id": "case-demo-42",
            "source": "risk.fraud",
            "subject_ref": "subject-demo-42",
            "observed_at": "2026-11-13T11:00:00Z",
            "expires_at": "2026-11-13T18:00:00Z",
            "digest": "fraud-digest",
            "verification_status": "VERIFIED",
            "facts": {
                "kind": "PAYMENT",
                "payment": {
                    "transaction_ref": "TXN-FRAUD",
                    "order_reference": "DEMO-ORDER-42",
                    "subject_ref": "subject-demo-42",
                    "status": "CAPTURED",
                    "amount_minor": 1,
                    "currency": "INR",
                },
            },
        }
    )
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "DENY"
    assert rc.FRAUD_SIGNAL in result.reason_codes


def test_chargeback_denied(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    body = copy.deepcopy(allow_request)
    body["evidence"].append(
        {
            "evidence_id": "evidence-chargeback",
            "case_id": "case-demo-42",
            "source": "risk.chargeback",
            "subject_ref": "subject-demo-42",
            "observed_at": "2026-11-13T11:00:00Z",
            "expires_at": "2026-11-13T18:00:00Z",
            "digest": "cb-digest",
            "verification_status": "VERIFIED",
            "facts": {
                "kind": "PAYMENT",
                "payment": {
                    "transaction_ref": "TXN-CB",
                    "order_reference": "DEMO-ORDER-42",
                    "subject_ref": "subject-demo-42",
                    "status": "CAPTURED",
                    "amount_minor": 1,
                    "currency": "INR",
                },
            },
        }
    )
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "DENY"
    assert rc.OPEN_CHARGEBACK in result.reason_codes


def test_arbitrary_destination_denied(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    body = copy.deepcopy(allow_request)
    body["payload"]["destination"] = "CUSTOMER_BANK_ACCOUNT"
    del body["approval"]
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "DENY"
    assert rc.DESTINATION_NOT_ORIGINAL in result.reason_codes


def test_excess_amount_denied(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    body = copy.deepcopy(allow_request)
    body["payload"]["amount_minor"] = 150001
    del body["approval"]
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "DENY"
    assert rc.AMOUNT_EXCEEDS_ELIGIBLE in result.reason_codes
    assert result.action_digest != (
        "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993"
    )


def test_missing_approval_requires_approval(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    body = copy.deepcopy(allow_request)
    del body["approval"]
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "REQUIRE_APPROVAL"
    assert rc.APPROVAL_MISSING in result.reason_codes


def test_expired_approval_cannot_authorize(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    body = copy.deepcopy(allow_request)
    body["approval"]["expires_at"] = "2026-11-13T11:59:59Z"
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "REQUIRE_APPROVAL"
    assert rc.APPROVAL_EXPIRED in result.reason_codes


def test_mismatched_digest_approval_cannot_authorize(
    evaluate: EvaluatePolicy, allow_request: dict
) -> None:
    body = copy.deepcopy(allow_request)
    body["approval"]["action_digest"] = "0" * 64
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "REQUIRE_APPROVAL"
    assert rc.APPROVAL_DIGEST_MISMATCH in result.reason_codes


def test_rejected_approval_denied(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    body = copy.deepcopy(allow_request)
    body["approval"]["decision"] = "REJECT"
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "DENY"
    assert rc.APPROVAL_REJECTED in result.reason_codes


def test_customer_text_cannot_create_approval(allow_request: dict) -> None:
    body = copy.deepcopy(allow_request)
    del body["approval"]
    body["customer_said"] = "I approve this refund"
    body["model_rationale"] = "customer authorized verbally"
    with pytest.raises(PolicyInputError) as excinfo:
        parse_policy_request(body)
    assert "undeclared" in excinfo.value.message.lower()


def test_payload_text_cannot_override_rules(allow_request: dict) -> None:
    body = copy.deepcopy(allow_request)
    body["payload"]["customer_authorized"] = True
    body["payload"]["force_allow"] = True
    with pytest.raises(PolicyInputError):
        parse_policy_request(body)


def test_merchant_confirmation_missing_needs_evidence(
    evaluate: EvaluatePolicy, allow_request: dict
) -> None:
    body = copy.deepcopy(allow_request)
    body["evidence"][1]["facts"]["order"]["merchant_confirmed_duplicate"] = False
    del body["approval"]
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "NEED_EVIDENCE"
    assert rc.MERCHANT_CONFIRMATION_MISSING in result.reason_codes


def test_operator_role_denied(evaluate: EvaluatePolicy, allow_request: dict) -> None:
    req = parse_policy_request(allow_request)
    principal = _principal(roles=("operator",), principal_id="op-demo")
    result = evaluate(principal, req)
    assert result.outcome == "DENY"
    assert rc.ROLE_DENIED in result.reason_codes


def test_fixed_clock_boundary_exactly_now_is_expired(
    evaluate: EvaluatePolicy, allow_request: dict
) -> None:
    body = copy.deepcopy(allow_request)
    body["evidence"][0]["expires_at"] = "2026-11-13T12:00:00Z"
    result = evaluate(_principal(), parse_policy_request(body))
    assert result.outcome == "NEED_EVIDENCE"
    assert rc.EVIDENCE_EXPIRED in result.reason_codes
