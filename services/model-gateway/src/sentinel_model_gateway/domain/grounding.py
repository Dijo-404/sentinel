"""Deterministic grounding of an LLM draft against the case evidence.

The model only chooses an outcome and points at a transaction. Money (amount, currency,
destination) and identity (case, revision) are copied from the request and evidence,
never from model text. Anything the evidence does not back becomes ESCALATE.
"""

from __future__ import annotations

from typing import Any

from .types import Evidence, ModelRequest, ModelResult, ProposalDraft


def _facts(item: Evidence, kind: str) -> dict[str, Any] | None:
    if item.verification_status != "VERIFIED" or item.facts.get("kind") != kind:
        return None
    body = item.facts.get(kind.lower())
    return body if isinstance(body, dict) else None


def _minor(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def escalate(request: ModelRequest, reason_code: str) -> ModelResult:
    return ModelResult(
        outcome="ESCALATE",
        reason_codes=[reason_code],
        original_text=request.input.original_text,
        language=request.input.language,
    )


def ground(request: ModelRequest, draft: ProposalDraft) -> ModelResult:
    if draft.outcome != "PROPOSAL":
        return ModelResult(
            outcome=draft.outcome,
            reason_codes=list(draft.reason_codes),
            original_text=request.input.original_text,
            language=request.input.language,
        )

    by_id = {e.evidence_id: e for e in request.evidence}
    cited = list(dict.fromkeys(draft.evidence_ids))
    if any(i not in by_id or by_id[i].verification_status != "VERIFIED" for i in cited):
        return escalate(request, "EVIDENCE_ID_INVALID")

    payments = [
        (e, p)
        for e in request.evidence
        if (p := _facts(e, "PAYMENT")) and p.get("transaction_ref") == draft.transaction_ref
    ]
    if not draft.transaction_ref or len(payments) != 1:
        return escalate(request, "TRANSACTION_NOT_IN_EVIDENCE")
    payment_evidence, payment = payments[0]
    if payment.get("order_reference") not in (None, request.input.order_reference):
        return escalate(request, "ORDER_REFERENCE_MISMATCH")
    if payment.get("status") != "CAPTURED" or payment.get("currency") != "INR":
        return escalate(request, "PAYMENT_NOT_REFUNDABLE")

    captured = _minor(payment.get("amount_minor"))
    # Pending and succeeded refunds both consume the refundable balance; only FAILED frees it.
    refunded = [
        _minor(r.get("amount_minor"))
        for e in request.evidence
        if (r := _facts(e, "REFUND"))
        and r.get("transaction_ref") == draft.transaction_ref
        and r.get("status") != "FAILED"
    ]
    if captured is None or None in refunded:
        return escalate(request, "AMOUNT_NOT_BACKED_BY_EVIDENCE")
    refundable = captured - sum(refunded)  # type: ignore[arg-type]
    if refundable < 1 or draft.amount_minor != refundable:
        return escalate(request, "AMOUNT_NOT_BACKED_BY_EVIDENCE")

    proposal = {
        "action": "REQUEST_REFUND",
        "case_id": request.case.case_id,
        "case_revision": request.input.case_revision,
        "transaction_ref": draft.transaction_ref,
        "amount_minor": refundable,
        "currency": "INR",
        "destination": "ORIGINAL_PAYMENT_ROUTE",
        # policy_version is left out on purpose: the workflow fills its own configured value.
        "evidence_ids": list(dict.fromkeys([*cited, payment_evidence.evidence_id])),
    }
    return ModelResult(
        outcome="PROPOSAL",
        proposal=proposal,
        reason_codes=list(draft.reason_codes),
        original_text=request.input.original_text,
        language=request.input.language,
    )
