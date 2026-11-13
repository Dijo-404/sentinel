"""Versioned local rules for demo-policy-v1. No framework imports."""

from __future__ import annotations

from datetime import UTC, datetime

from sentinel_policy.contracts import (
    POLICY_VERSION,
    Approval,
    Evidence,
    GenericAction,
    PolicyRequest,
    PolicyResult,
    Principal,
    RefundAction,
    action_digest,
)
from sentinel_policy.domain import reason_codes as rc

FRAUD_SOURCES = frozenset({"risk.fraud", "fraud.signal", "fraud.engine"})
CHARGEBACK_SOURCES = frozenset({"risk.chargeback", "chargeback.open", "dispute.chargeback"})


def _parse_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _result(
    outcome: str,
    reasons: list[str],
    digest: str,
    required: list[str] | None = None,
) -> PolicyResult:
    return PolicyResult(
        outcome=outcome,  # type: ignore[arg-type]
        reason_codes=tuple(reasons),
        policy_version=POLICY_VERSION,
        action_digest=digest,
        required_evidence=tuple(required or ()),
    )


def _scope_denied(principal: Principal, case_id: str, evidence: tuple[Evidence, ...]) -> str | None:
    if "workflow" not in principal.roles:
        return rc.ROLE_DENIED
    if case_id not in principal.case_ids:
        return rc.CASE_SCOPE_DENIED
    for item in evidence:
        if item.case_id != case_id:
            return rc.EVIDENCE_CASE_MISMATCH
        if item.subject_ref not in principal.subject_refs:
            return rc.SUBJECT_SCOPE_DENIED
    return None


def _evidence_by_id(evidence: tuple[Evidence, ...]) -> dict[str, Evidence]:
    return {item.evidence_id: item for item in evidence}


def _payment_facts(item: Evidence) -> dict | None:
    facts = item.facts
    if facts.get("kind") != "PAYMENT":
        return None
    payment = facts.get("payment")
    return payment if isinstance(payment, dict) else None


def _order_facts(item: Evidence) -> dict | None:
    facts = item.facts
    if facts.get("kind") != "ORDER":
        return None
    order = facts.get("order")
    return order if isinstance(order, dict) else None


def _refund_alloc_minor(evidence: tuple[Evidence, ...], transaction_ref: str) -> int:
    total = 0
    for item in evidence:
        facts = item.facts
        if facts.get("kind") != "REFUND":
            continue
        refund = facts.get("refund")
        if not isinstance(refund, dict):
            continue
        if refund.get("transaction_ref") != transaction_ref:
            continue
        status = refund.get("status")
        amount = refund.get("amount_minor")
        if status in {"PENDING", "PROVIDER_CONFIRMED"} and isinstance(amount, int):
            total += amount
    return total


def _risk_codes(evidence: tuple[Evidence, ...]) -> list[str]:
    codes: list[str] = []
    for item in evidence:
        source = item.source
        if source in FRAUD_SOURCES or source.startswith("risk.fraud"):
            codes.append(rc.FRAUD_SIGNAL)
        if source in CHARGEBACK_SOURCES or source.startswith("risk.chargeback"):
            codes.append(rc.OPEN_CHARGEBACK)
        if item.verification_status == "CONFLICTING" and "chargeback" in source:
            codes.append(rc.OPEN_CHARGEBACK)
    # stable unique order
    seen: set[str] = set()
    ordered: list[str] = []
    for code in codes:
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def _freshness_and_status(
    selected: list[Evidence],
    now: datetime,
) -> tuple[list[str], list[str]]:
    reasons: list[str] = []
    required: list[str] = []
    for item in selected:
        if _parse_utc(item.expires_at) <= now:
            reasons.append(rc.EVIDENCE_EXPIRED)
            required.append(item.evidence_id)
            continue
        if item.verification_status == "UNVERIFIED":
            reasons.append(rc.EVIDENCE_UNVERIFIED)
            required.append(item.evidence_id)
        elif item.verification_status == "CONFLICTING":
            reasons.append(rc.EVIDENCE_CONFLICTING)
            required.append(item.evidence_id)
    return reasons, required


def _approval_outcome(
    approval: Approval | None,
    digest: str,
    case_revision: int,
    now: datetime,
) -> PolicyResult | None:
    """Return a terminal PolicyResult when approval blocks ALLOW; None if approval authorizes."""
    if approval is None:
        return _result("REQUIRE_APPROVAL", [rc.APPROVAL_MISSING], digest)
    reasons: list[str] = []
    if approval.action_digest != digest:
        reasons.append(rc.APPROVAL_DIGEST_MISMATCH)
    if approval.case_revision != case_revision:
        reasons.append(rc.APPROVAL_REVISION_MISMATCH)
    if approval.policy_version != POLICY_VERSION:
        reasons.append(rc.APPROVAL_POLICY_MISMATCH)
    if _parse_utc(approval.expires_at) <= now:
        reasons.append(rc.APPROVAL_EXPIRED)
    if approval.decision == "REJECT":
        reasons.append(rc.APPROVAL_REJECTED)
    if reasons:
        # Missing/expired/mismatched approval cannot authorize a refund.
        if rc.APPROVAL_REJECTED in reasons and len(reasons) == 1:
            return _result("DENY", reasons, digest)
        if set(reasons) <= {
            rc.APPROVAL_EXPIRED,
            rc.APPROVAL_DIGEST_MISMATCH,
            rc.APPROVAL_REVISION_MISMATCH,
            rc.APPROVAL_POLICY_MISMATCH,
        }:
            return _result("REQUIRE_APPROVAL", reasons, digest)
        return _result("DENY", reasons, digest)
    return None


def evaluate_refund(
    principal: Principal,
    action: RefundAction,
    evidence: tuple[Evidence, ...],
    approval: Approval | None,
    now: datetime,
) -> PolicyResult:
    digest = action_digest(action.as_digest_dict())

    scope = _scope_denied(principal, action.case_id, evidence)
    if scope == rc.ROLE_DENIED:
        return _result("DENY", [rc.ROLE_DENIED], digest)
    if scope == rc.CASE_SCOPE_DENIED:
        return _result("DENY", [rc.TENANT_SCOPE_DENIED], digest)
    if scope == rc.SUBJECT_SCOPE_DENIED:
        return _result("DENY", [rc.SUBJECT_SCOPE_DENIED], digest)
    if scope == rc.EVIDENCE_CASE_MISMATCH:
        return _result("DENY", [rc.EVIDENCE_CASE_MISMATCH], digest)

    if action.policy_version != POLICY_VERSION:
        return _result("DENY", [rc.POLICY_VERSION_UNSUPPORTED], digest)

    if action.destination != "ORIGINAL_PAYMENT_ROUTE":
        return _result("DENY", [rc.DESTINATION_NOT_ORIGINAL], digest)

    if action.currency != "INR":
        return _result("DENY", [rc.CURRENCY_UNSUPPORTED], digest)

    if action.amount_minor <= 0:
        return _result("DENY", [rc.AMOUNT_INVALID], digest)

    by_id = _evidence_by_id(evidence)
    missing_ids = [eid for eid in action.evidence_ids if eid not in by_id]
    if missing_ids:
        return _result(
            "NEED_EVIDENCE",
            [rc.EVIDENCE_ID_MISMATCH],
            digest,
            required=missing_ids,
        )

    selected = [by_id[eid] for eid in action.evidence_ids]
    risk = _risk_codes(evidence)
    if risk:
        return _result("DENY", risk, digest)

    fresh_reasons, required = _freshness_and_status(selected, now)
    if rc.EVIDENCE_CONFLICTING in fresh_reasons:
        return _result("DENY", [rc.EVIDENCE_CONFLICTING], digest, required=required)
    if fresh_reasons:
        # Expired or unverified required evidence.
        outcome = "NEED_EVIDENCE"
        return _result(outcome, fresh_reasons, digest, required=required)

    payment_item = None
    payment = None
    for item in selected:
        candidate = _payment_facts(item)
        if candidate and candidate.get("transaction_ref") == action.transaction_ref:
            payment_item = item
            payment = candidate
            break
    if payment is None or payment_item is None:
        return _result(
            "NEED_EVIDENCE",
            [rc.PAYMENT_EVIDENCE_MISSING],
            digest,
            required=["payment"],
        )

    status = payment.get("status")
    if status == "PENDING":
        return _result("DENY", [rc.PAYMENT_PENDING], digest)
    if status == "FAILED":
        return _result("DENY", [rc.PAYMENT_FAILED], digest)
    if status != "CAPTURED":
        return _result("DENY", [rc.PAYMENT_NOT_CAPTURED], digest)

    amount = payment.get("amount_minor")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        return _result("DENY", [rc.AMOUNT_INVALID], digest)

    allocated = _refund_alloc_minor(evidence, action.transaction_ref)
    eligible = amount - allocated
    if action.amount_minor > eligible:
        return _result("DENY", [rc.AMOUNT_EXCEEDS_ELIGIBLE], digest)

    order = None
    for item in selected:
        candidate = _order_facts(item)
        if candidate is not None:
            order = candidate
            break
    if order is None:
        return _result(
            "NEED_EVIDENCE",
            [rc.ORDER_EVIDENCE_MISSING],
            digest,
            required=["order"],
        )
    if order.get("merchant_confirmed_duplicate") is not True:
        return _result(
            "NEED_EVIDENCE",
            [rc.MERCHANT_CONFIRMATION_MISSING],
            digest,
            required=["merchant_confirmation"],
        )

    blocked = _approval_outcome(approval, digest, action.case_revision, now)
    if blocked is not None:
        return blocked

    return _result("ALLOW", [rc.REFUND_APPROVED], digest)


def evaluate_non_refund(
    principal: Principal,
    action: GenericAction,
    evidence: tuple[Evidence, ...],
    now: datetime,
) -> PolicyResult:
    digest = action_digest(action.as_digest_dict())
    scope = _scope_denied(principal, action.case_id, evidence)
    if scope is not None:
        code = rc.TENANT_SCOPE_DENIED if scope == rc.CASE_SCOPE_DENIED else scope
        return _result("DENY", [code], digest)
    if action.policy_version != POLICY_VERSION:
        return _result("DENY", [rc.POLICY_VERSION_UNSUPPORTED], digest)
    risk = _risk_codes(evidence)
    if risk:
        return _result("DENY", risk, digest)
    # Non-refund actions do not mint financial authority.
    return _result("ALLOW", [rc.NON_REFUND_ALLOWED], digest)


def evaluate_policy(
    principal: Principal,
    request: PolicyRequest,
    now: datetime,
) -> PolicyResult:
    payload = request.payload
    if isinstance(payload, RefundAction):
        return evaluate_refund(
            principal,
            payload,
            request.evidence,
            request.approval,
            now,
        )
    return evaluate_non_refund(principal, payload, request.evidence, now)
