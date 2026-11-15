"""Deterministic grounding of an LLM draft against the case evidence.

The model only chooses an outcome and points at a transaction. Money (amount, currency,
destination) and identity (case, revision) are copied from the request and evidence,
never from model text. Anything the evidence does not back becomes ESCALATE.
"""

from __future__ import annotations

from typing import Any

from .types import Evidence, ModelRequest, ModelResult, ProposalDraft


def split_order_reference(authorized_reference: str) -> tuple[str, str] | None:
    """Split a case order_reference ``{subject_ref}/{order_id}`` (or ``:``).

    Exactly one separator and two non-empty parts; anything else -> None.
    Provider payments carry the bare ``order_id`` plus their own ``subject_ref``.
    """
    ref = authorized_reference
    if not isinstance(ref, str) or not ref or ref != ref.strip():
        return None
    if ref.count("/") + ref.count(":") != 1:
        return None
    subject, _, order = ref.partition("/") if "/" in ref else ref.partition(":")
    if not subject or not order:
        return None
    return subject, order


def _facts(item: Evidence, kind: str) -> dict[str, Any] | None:
    if item.verification_status != "VERIFIED" or item.facts.get("kind") != kind:
        return None
    body = item.facts.get(kind.lower())
    return body if isinstance(body, dict) else None


def _minor(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


# evidence.v1 / simulator RefundStatus. Pending and confirmed refunds consume the balance.
_REFUND_COUNTED = frozenset({"PENDING", "PROVIDER_CONFIRMED"})
_REFUND_RELEASED = frozenset({"FAILED_FINAL"})


def _refunded_minor(request: ModelRequest, transaction_ref: str) -> int | None:
    """Sum of pending + completed refunds on the transaction; None if any refund is unusable."""
    total = 0
    for item in request.evidence:
        if item.facts.get("kind") != "REFUND":
            continue
        refund = item.facts.get("refund")
        if not isinstance(refund, dict):
            return None
        if refund.get("transaction_ref") != transaction_ref:
            continue
        status, amount = refund.get("status"), _minor(refund.get("amount_minor"))
        # Never skip unverified or unrecognised refunds: that could hide money already out.
        if (
            item.verification_status != "VERIFIED"
            or status not in _REFUND_COUNTED | _REFUND_RELEASED
            or amount is None
            or refund.get("currency") != "INR"
        ):
            return None
        if status in _REFUND_COUNTED:
            total += amount
    return total


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
    if not payment.get("order_reference"):
        return escalate(request, "ORDER_REFERENCE_MISSING")
    case_ref = request.input.order_reference
    if isinstance(case_ref, str) and "/" not in case_ref and ":" not in case_ref:
        return escalate(request, "ORDER_REFERENCE_UNBOUND")
    bound = split_order_reference(case_ref)
    if bound is None:
        return escalate(request, "ORDER_REFERENCE_INVALID")
    subject_ref, provider_order = bound
    # Ownership: the payment must belong to the case's subject, not just share an order id.
    if (
        payment_evidence.subject_ref != subject_ref
        or payment.get("subject_ref", subject_ref) != subject_ref
    ):
        return escalate(request, "SUBJECT_MISMATCH")
    if payment["order_reference"] != provider_order:
        return escalate(request, "ORDER_REFERENCE_MISMATCH")
    if payment.get("status") != "CAPTURED" or payment.get("currency") != "INR":
        return escalate(request, "PAYMENT_NOT_REFUNDABLE")

    refunded = _refunded_minor(request, draft.transaction_ref)
    if refunded is None:
        return escalate(request, "REFUND_EVIDENCE_UNVERIFIED")
    captured = _minor(payment.get("amount_minor"))
    if captured is None:
        return escalate(request, "AMOUNT_NOT_BACKED_BY_EVIDENCE")
    refundable = captured - refunded
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
