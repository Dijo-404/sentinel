"""Deterministic case invariants."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .types import (
    CASE_STATES,
    CHANNELS,
    OWNER_QUEUES,
    CaseCreate,
    CaseResult,
    DecisionRequest,
    DomainError,
    VerificationResult,
)


def case_states() -> frozenset[str]:
    return CASE_STATES


def _require_nonempty(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainError("INVALID_INPUT", f"{name} is required", 422)
    return value


def validate_case_create(body: dict[str, Any]) -> CaseCreate:
    if set(body) - {"message", "language", "order_reference", "channel"}:
        raise DomainError("INVALID_INPUT", "Undeclared CaseCreate fields", 422)
    message = _require_nonempty("message", body.get("message"))
    language = _require_nonempty("language", body.get("language"))
    order_reference = _require_nonempty("order_reference", body.get("order_reference"))
    channel = body.get("channel")
    if channel not in CHANNELS:
        raise DomainError("INVALID_INPUT", "channel must be web or voice", 422)
    return CaseCreate(
        message=message,
        language=language,
        order_reference=order_reference,
        channel=channel,  # type: ignore[arg-type]
    )


def order_bound_to_subject(order_reference: str, subject_ref: str) -> bool:
    """True when order_reference equals subject_ref or is subject-prefixed with a boundary.

    Canonical authorized form for customer intake: ``{subject_ref}/{customer_order_id}``
    (example: ``subject-a/DEMO-ORDER-42``). Colon boundary (``subject-a:42``) also binds.
    Bare provider ids (``DEMO-ORDER-42``) are not bound and must not be invented or stripped
    into that shape at enqueue — preserve the authorized intake value through CaseInput
    and workflow outbox scheduling payloads.
    """
    if order_reference == subject_ref:
        return True
    return order_reference.startswith(f"{subject_ref}/") or order_reference.startswith(
        f"{subject_ref}:"
    )


def require_order_bound_to_principal(
    order_reference: str,
    *,
    subject_refs: tuple[str, ...],
    enforce: bool,
) -> None:
    """Fail closed: scoped principals may only open cases on their own orders.

    Call with enforce=True for customers, or whenever subject_refs is non-empty.
    Operators with empty subject_refs skip (enforce=False).
    """
    if not enforce:
        return
    if not subject_refs:
        raise DomainError("FORBIDDEN", "order_reference not bound to principal", 403)
    if not any(order_bound_to_subject(order_reference, ref) for ref in subject_refs):
        raise DomainError("FORBIDDEN", "order_reference not bound to principal", 403)


def validate_message(body: dict[str, Any]) -> tuple[str, str, int]:
    if set(body) - {"message", "language", "expected_revision"}:
        raise DomainError("INVALID_INPUT", "Undeclared message fields", 422)
    message = _require_nonempty("message", body.get("message"))
    language = _require_nonempty("language", body.get("language"))
    revision = body.get("expected_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise DomainError("INVALID_INPUT", "expected_revision must be a positive int", 422)
    return message, language, revision


def validate_escalate(body: dict[str, Any]) -> tuple[int, str, str]:
    if set(body) - {"expected_revision", "reason_code", "owner_queue"}:
        raise DomainError("INVALID_INPUT", "Undeclared escalate fields", 422)
    revision = body.get("expected_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise DomainError("INVALID_INPUT", "expected_revision must be a positive int", 422)
    reason = _require_nonempty("reason_code", body.get("reason_code"))
    queue = body.get("owner_queue")
    if queue not in OWNER_QUEUES:
        raise DomainError("INVALID_INPUT", "owner_queue must be PAYMENTS|FRAUD|SUPERVISOR", 422)
    return revision, reason, str(queue)


def validate_decision_request(body: dict[str, Any]) -> DecisionRequest:
    allowed = {"decision", "action_digest", "case_revision", "policy_version", "expires_at"}
    if set(body) - allowed:
        raise DomainError("INVALID_INPUT", "Undeclared DecisionRequest fields", 422)
    decision = body.get("decision")
    if decision not in {"APPROVE", "REJECT"}:
        raise DomainError("INVALID_INPUT", "decision must be APPROVE or REJECT", 422)
    digest = _require_nonempty("action_digest", body.get("action_digest"))
    revision = body.get("case_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise DomainError("INVALID_INPUT", "case_revision must be a positive int", 422)
    policy = _require_nonempty("policy_version", body.get("policy_version"))
    expires = _require_nonempty("expires_at", body.get("expires_at"))
    return DecisionRequest(
        decision=decision,  # type: ignore[arg-type]
        action_digest=digest,
        case_revision=revision,
        policy_version=policy,
        expires_at=expires,
    )


def validate_result(body: dict[str, Any]) -> CaseResult:
    allowed = {
        "event_key",
        "expected_revision",
        "status",
        "evidence_ids",
        "action_id",
        "assessment_id",
        "reason_code",
    }
    if set(body) - allowed:
        raise DomainError("INVALID_INPUT", "Undeclared CaseResult fields", 422)
    event_key = _require_nonempty("event_key", body.get("event_key"))
    revision = body.get("expected_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise DomainError("INVALID_INPUT", "expected_revision must be a positive int", 422)
    status = body.get("status")
    if status not in CASE_STATES:
        raise DomainError("INVALID_INPUT", "status is not a CaseState", 422)
    evidence_ids = body.get("evidence_ids")
    if not isinstance(evidence_ids, list) or not all(isinstance(x, str) for x in evidence_ids):
        raise DomainError("INVALID_INPUT", "evidence_ids must be a string array", 422)
    reason = _require_nonempty("reason_code", body.get("reason_code"))
    action_id = body.get("action_id")
    if action_id is not None and (not isinstance(action_id, str) or not action_id):
        raise DomainError("INVALID_INPUT", "action_id must be a nonempty string when set", 422)
    assessment_id = body.get("assessment_id")
    if assessment_id is not None and (not isinstance(assessment_id, str) or not assessment_id):
        raise DomainError("INVALID_INPUT", "assessment_id must be a nonempty string when set", 422)
    if status == "VERIFIED_RESOLVED" and not assessment_id:
        raise DomainError(
            "INVALID_INPUT",
            "VERIFIED_RESOLVED requires assessment_id",
            422,
        )
    return CaseResult(
        event_key=event_key,
        expected_revision=revision,
        status=str(status),
        evidence_ids=tuple(evidence_ids),
        reason_code=reason,
        action_id=action_id,
        assessment_id=assessment_id,
    )


def idempotency_payload_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _canonical(left) == _canonical(right)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _parse_rfc3339(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def assert_verified_resolution(
    *,
    result: CaseResult,
    case_id: str,
    assessment: VerificationResult,
    now: datetime,
) -> None:
    """Trusted verifier assessment must match case/action/revision and stay fresh."""
    if assessment.assessment_id != result.assessment_id:
        raise DomainError("ASSESSMENT_MISMATCH", "assessment_id does not match", 422)
    if assessment.case_id != case_id:
        raise DomainError("ASSESSMENT_MISMATCH", "assessment case_id mismatch", 422)
    if assessment.case_revision != result.expected_revision:
        raise DomainError("ASSESSMENT_MISMATCH", "assessment case_revision mismatch", 422)
    if result.action_id is None or assessment.action_id != result.action_id:
        raise DomainError("ASSESSMENT_MISMATCH", "assessment action_id mismatch", 422)
    if assessment.status != "VERIFIED":
        raise DomainError("ASSESSMENT_NOT_VERIFIED", "assessment is not VERIFIED", 422)
    try:
        expires = _parse_rfc3339(assessment.expires_at)
    except ValueError as exc:
        raise DomainError("ASSESSMENT_INVALID", "assessment expires_at is invalid", 422) from exc
    if expires.tzinfo is None or now.tzinfo is None:
        raise DomainError("ASSESSMENT_INVALID", "timestamps require timezone", 422)
    if expires <= now:
        raise DomainError("ASSESSMENT_EXPIRED", "assessment is expired", 422)
    if not assessment.evidence:
        raise DomainError("ASSESSMENT_INVALID", "assessment requires verified evidence", 422)
    kinds: set[str | None] = set()
    for item in assessment.evidence:
        if item.get("verification_status") != "VERIFIED":
            raise DomainError("ASSESSMENT_INVALID", "evidence is not VERIFIED", 422)
        try:
            evidence_expires = _parse_rfc3339(str(item["expires_at"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise DomainError("ASSESSMENT_INVALID", "evidence expiry invalid", 422) from exc
        if evidence_expires <= now:
            raise DomainError("ASSESSMENT_EXPIRED", "evidence is expired", 422)
        facts = item.get("facts")
        kinds.add(facts.get("kind") if isinstance(facts, dict) else None)
    # Scenario predicate: verified resolution needs refund or credit evidence.
    if "CREDIT" not in kinds and "REFUND" not in kinds:
        raise DomainError(
            "ASSESSMENT_INCOMPLETE",
            "verified resolution requires refund or credit evidence",
            422,
        )
