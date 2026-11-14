"""Domain invariants for investigations, findings and restrictions."""

from __future__ import annotations

from datetime import datetime, timedelta

from .types import (
    FINDING_CLASSIFICATIONS,
    RESTRICTION_DECISIONS,
    FindingClassification,
    Investigation,
    RestrictionDecision,
    RiskRestriction,
)


def format_rfc3339(instant: datetime) -> str:
    return instant.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_rfc3339(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("timestamp must use Z suffix")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def default_review_due(now: datetime, *, hours: int = 72) -> str:
    return format_rfc3339(now + timedelta(hours=hours))


def assert_classification(value: str) -> FindingClassification:
    if value not in FINDING_CLASSIFICATIONS:
        raise ValueError(
            "classification must be LEGITIMATE, INSUFFICIENT_EVIDENCE, "
            "SUSPICIOUS, or CONFIRMED_FRAUD"
        )
    return value  # type: ignore[return-value]


def assert_decision(value: str) -> RestrictionDecision:
    if value not in RESTRICTION_DECISIONS:
        raise ValueError("decision must be CLEAR, MAINTAIN, or CONFIRM_FRAUD")
    return value  # type: ignore[return-value]


def assert_can_record_finding(investigation: Investigation) -> None:
    if investigation.status == "CLOSED":
        raise ValueError("Cannot record finding on closed investigation")


def assert_can_decide(
    restriction: RiskRestriction,
    investigation: Investigation,
    *,
    expected_revision: int,
) -> None:
    if investigation.investigation_id != restriction.investigation_id:
        raise ValueError("Restriction does not belong to investigation")
    if restriction.revision != expected_revision:
        raise ValueError("Restriction revision mismatch")
    if restriction.status == "CLEARED":
        raise ValueError("Restriction already cleared")


def apply_restriction_decision(
    restriction: RiskRestriction,
    *,
    decision: RestrictionDecision,
    actor_id: str,
    reason: str,
    evidence_ids: tuple[str, ...],
    decided_at: str,
) -> RiskRestriction:
    """Apply risk decision. Clearance never grants financial approval."""
    if decision == "CLEAR":
        return RiskRestriction(
            restriction_id=restriction.restriction_id,
            tenant_id=restriction.tenant_id,
            case_id=restriction.case_id,
            investigation_id=restriction.investigation_id,
            reason_code=restriction.reason_code,
            status="CLEARED",
            blocks_financial_actions=False,
            created_at=restriction.created_at,
            review_due_at=restriction.review_due_at,
            created_by=restriction.created_by,
            policy_version=restriction.policy_version,
            evidence_ids=evidence_ids or restriction.evidence_ids,
            revision=restriction.revision + 1,
            transaction_ref=restriction.transaction_ref,
            action_id=restriction.action_id,
            cleared_by=actor_id,
            clearance_reason=reason,
            financial_approval_granted=False,
        )
    if decision == "MAINTAIN":
        return RiskRestriction(
            restriction_id=restriction.restriction_id,
            tenant_id=restriction.tenant_id,
            case_id=restriction.case_id,
            investigation_id=restriction.investigation_id,
            reason_code=restriction.reason_code,
            status="MAINTAINED",
            blocks_financial_actions=True,
            created_at=restriction.created_at,
            review_due_at=restriction.review_due_at,
            created_by=restriction.created_by,
            policy_version=restriction.policy_version,
            evidence_ids=evidence_ids or restriction.evidence_ids,
            revision=restriction.revision + 1,
            transaction_ref=restriction.transaction_ref,
            action_id=restriction.action_id,
            cleared_by=None,
            clearance_reason=None,
            financial_approval_granted=False,
        )
    # CONFIRM_FRAUD
    return RiskRestriction(
        restriction_id=restriction.restriction_id,
        tenant_id=restriction.tenant_id,
        case_id=restriction.case_id,
        investigation_id=restriction.investigation_id,
        reason_code=restriction.reason_code,
        status="ACTIVE",
        blocks_financial_actions=True,
        created_at=restriction.created_at,
        review_due_at=restriction.review_due_at,
        created_by=restriction.created_by,
        policy_version=restriction.policy_version,
        evidence_ids=evidence_ids or restriction.evidence_ids,
        revision=restriction.revision + 1,
        transaction_ref=restriction.transaction_ref,
        action_id=restriction.action_id,
        cleared_by=None,
        clearance_reason=None,
        financial_approval_granted=False,
    )


def investigation_status_after_finding(
    classification: FindingClassification,
) -> str:
    if classification == "LEGITIMATE":
        return "UNDER_REVIEW"
    if classification == "INSUFFICIENT_EVIDENCE":
        return "AWAITING_EVIDENCE"
    if classification == "CONFIRMED_FRAUD":
        return "CLOSED"
    return "UNDER_REVIEW"


def case_is_blocked(
    restrictions: tuple[RiskRestriction, ...],
    *,
    case_id: str,
) -> bool:
    return any(
        r.case_id == case_id and r.blocks_financial_actions and r.status in {"ACTIVE", "MAINTAINED"}
        for r in restrictions
    )
