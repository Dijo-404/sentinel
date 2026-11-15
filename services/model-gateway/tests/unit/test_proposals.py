"""POST /v1/proposals: grounding, retry, fail-closed and auth behavior."""

from __future__ import annotations

import httpx
import pytest

from tests.conftest import AUTH, FAKE_KEY, _payment, draft, model_request


def _post(client, body=None, headers=AUTH):
    return client.post("/v1/proposals", json=body or model_request(), headers=headers)


def test_valid_proposal_copies_money_from_evidence(client, sarvam):
    sarvam.queue.append(draft())
    response = _post(client)
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "PROPOSAL"
    assert body["proposal"] == {
        "action": "REQUEST_REFUND",
        "case_id": "case-demo-42",
        "case_revision": 1,
        "transaction_ref": "TXN-B",
        "amount_minor": 150000,
        "currency": "INR",
        "destination": "ORIGINAL_PAYMENT_ROUTE",
        "evidence_ids": ["evidence-payment-b", "evidence-order"],
    }
    assert body["reason_codes"] == ["DUPLICATE_PAYMENT"]
    assert body["original_text"] == "I was charged twice for order DEMO-ORDER-42"
    # Sarvam called with configured model, key header, generous max_tokens.
    [request] = sarvam.requests
    assert request.headers["api-subscription-key"] == FAKE_KEY
    sent = sarvam.bodies()[0]
    assert sent["model"] == "sarvam-test-model"
    assert sent["max_tokens"] == 4096
    assert sent["reasoning_effort"] is None  # default off: callers time out at 10s
    assert "TXN-B" in sent["messages"][1]["content"]


def test_payment_evidence_id_is_always_cited(client, sarvam):
    sarvam.queue.append(draft(evidence_ids=["evidence-order"]))
    body = _post(client).json()
    assert body["proposal"]["evidence_ids"] == ["evidence-order", "evidence-payment-b"]


@pytest.mark.parametrize("amount", [999999, 149999, 0, None])
def test_amount_not_backed_by_evidence_escalates(client, sarvam, amount):
    sarvam.queue.append(draft(amount_minor=amount))
    body = _post(client).json()
    assert body["outcome"] == "ESCALATE"
    assert body["reason_codes"] == ["AMOUNT_NOT_BACKED_BY_EVIDENCE"]
    assert "proposal" not in body


def test_amount_as_string_is_malformed_not_coerced(client, sarvam):
    sarvam.queue.extend([draft(amount_minor="150000"), draft(amount_minor="150000")])
    body = _post(client).json()
    assert body == {**body, "outcome": "ESCALATE", "reason_codes": ["MODEL_OUTPUT_INVALID"]}


def _with_refund(request, refund_id="evidence-refund-1", verification="VERIFIED", **fields):
    refund = _payment(refund_id, "TXN-B")
    refund["verification_status"] = verification
    body = {"transaction_ref": "TXN-B", "amount_minor": 50000, "currency": "INR"}
    body.update(fields)
    refund["facts"] = {"kind": "REFUND", "refund": {k: v for k, v in body.items() if v != ...}}
    request["evidence"].append(refund)
    return request


@pytest.mark.parametrize("status", ["PENDING", "PROVIDER_CONFIRMED"])
def test_pending_and_completed_refunds_reduce_refundable_balance(client, sarvam, status):
    request = _with_refund(model_request(), status=status)
    sarvam.queue.append(draft(amount_minor=150000))
    assert _post(client, request).json()["reason_codes"] == ["AMOUNT_NOT_BACKED_BY_EVIDENCE"]
    sarvam.queue.append(draft(amount_minor=100000))
    assert _post(client, request).json()["proposal"]["amount_minor"] == 100000


def test_pending_plus_completed_refunds_both_count(client, sarvam):
    request = _with_refund(model_request(), status="PROVIDER_CONFIRMED")
    request = _with_refund(request, "evidence-refund-2", status="PENDING", amount_minor=60000)
    sarvam.queue.append(draft(amount_minor=40000))
    assert _post(client, request).json()["proposal"]["amount_minor"] == 40000


def test_final_failed_refund_frees_balance(client, sarvam):
    request = _with_refund(model_request(), status="FAILED_FINAL")
    sarvam.queue.append(draft(amount_minor=150000))
    assert _post(client, request).json()["proposal"]["amount_minor"] == 150000


@pytest.mark.parametrize(
    "fields,verification",
    [
        ({"status": ...}, "VERIFIED"),  # missing status
        ({"status": "FAILED"}, "VERIFIED"),  # not a recognised provider status
        ({"status": "REVERSED"}, "VERIFIED"),
        ({"status": "PENDING", "amount_minor": "50000"}, "VERIFIED"),
        ({"status": "PENDING", "currency": "USD"}, "VERIFIED"),
        ({"status": "PENDING"}, "UNVERIFIED"),  # unverified refund must not be ignored
        ({"status": "PENDING"}, "CONFLICTING"),
    ],
)
def test_unrecognised_refund_evidence_escalates(client, sarvam, fields, verification):
    request = _with_refund(model_request(), verification=verification, **fields)
    sarvam.queue.append(draft(amount_minor=150000))
    body = _post(client, request).json()
    assert body["outcome"] == "ESCALATE"
    assert body["reason_codes"] == ["REFUND_EVIDENCE_UNVERIFIED"]


def test_unknown_transaction_escalates(client, sarvam):
    sarvam.queue.append(draft(transaction_ref="TXN-INVENTED"))
    assert _post(client).json()["reason_codes"] == ["TRANSACTION_NOT_IN_EVIDENCE"]


def test_hallucinated_evidence_id_escalates(client, sarvam):
    sarvam.queue.append(draft(evidence_ids=["evidence-payment-b", "evidence-made-up"]))
    assert _post(client).json()["reason_codes"] == ["EVIDENCE_ID_INVALID"]


def test_unverified_payment_is_not_refundable(client, sarvam):
    request = model_request()
    request["evidence"][1]["verification_status"] = "CONFLICTING"
    sarvam.queue.append(draft(evidence_ids=[]))
    assert _post(client, request).json()["reason_codes"] == ["TRANSACTION_NOT_IN_EVIDENCE"]


def test_other_order_payment_escalates(client, sarvam):
    request = model_request()
    request["evidence"][1]["facts"]["payment"]["order_reference"] = "OTHER-ORDER"
    sarvam.queue.append(draft())
    assert _post(client, request).json()["reason_codes"] == ["ORDER_REFERENCE_MISMATCH"]


@pytest.mark.parametrize("value", [..., None, ""])
def test_payment_without_order_reference_escalates(client, sarvam, value):
    request = model_request()
    payment = request["evidence"][1]["facts"]["payment"]
    if value is ...:
        del payment["order_reference"]
    else:
        payment["order_reference"] = value
    sarvam.queue.append(draft())
    assert _post(client, request).json()["reason_codes"] == ["ORDER_REFERENCE_MISSING"]


def test_needs_input_passes_through_without_proposal(client, sarvam):
    sarvam.queue.append(
        draft(outcome="NEEDS_INPUT", transaction_ref=None, reason_codes=["AMBIGUOUS_TRANSACTION"])
    )
    body = _post(client).json()
    assert body["outcome"] == "NEEDS_INPUT"
    assert body["reason_codes"] == ["AMBIGUOUS_TRANSACTION"]
    assert "proposal" not in body


def test_malformed_json_retried_once_then_succeeds(client, sarvam):
    sarvam.queue.extend(["Sure! Here is the refund.", "```json\n" + draft() + "\n```"])
    body = _post(client).json()
    assert body["outcome"] == "PROPOSAL"
    assert len(sarvam.requests) == 2
    retry_messages = sarvam.bodies()[1]["messages"]
    assert retry_messages[-2] == {"role": "assistant", "content": "Sure! Here is the refund."}


def test_malformed_json_twice_fails_closed_to_escalate(client, sarvam):
    sarvam.queue.extend(["not json", '{"outcome": "REFUND_NOW"}'])
    response = _post(client)
    assert response.status_code == 200
    assert response.json()["outcome"] == "ESCALATE"
    assert response.json()["reason_codes"] == ["MODEL_OUTPUT_INVALID"]
    assert len(sarvam.requests) == 2


def test_empty_content_from_token_exhaustion_fails_closed(client, sarvam):
    sarvam.queue.extend(["", ""])
    assert _post(client).json()["reason_codes"] == ["MODEL_OUTPUT_INVALID"]


@pytest.mark.parametrize(
    "failure", [500, 503, 429, 401, httpx.ReadTimeout("slow"), httpx.ConnectError("down")]
)
def test_sarvam_failure_is_503_for_workflow_retry(client, sarvam, failure):
    sarvam.queue.append(failure)
    response = _post(client)
    assert response.status_code == 503
    assert response.json()["code"] == "UPSTREAM_UNAVAILABLE"
    assert FAKE_KEY not in response.text


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer wrong"}, {"Authorization": "tok-gateway-test"}]
)
def test_unauthorized_caller_rejected_before_model_call(client, sarvam, headers):
    response = _post(client, headers=headers)
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"
    assert sarvam.requests == []


def test_unauthorized_beats_invalid_body(client, sarvam):
    response = client.post("/v1/proposals", json={"nope": 1})
    assert response.status_code == 401


def test_invalid_model_request_is_422(client, sarvam):
    response = client.post("/v1/proposals", json={"case": {}}, headers=AUTH)
    assert response.status_code == 422
    assert sarvam.requests == []
