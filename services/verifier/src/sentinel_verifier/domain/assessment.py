"""Closure assessment rules. Pending refund is never customer credit."""

from __future__ import annotations

from typing import Any

from sentinel_verifier.domain.types import AssessmentStatus, Credit, Refund


def classify_outcomes(
    *,
    action_status: str,
    refund: Refund | None,
    credit: Credit | None,
    evidence: list[dict[str, Any]],
) -> tuple[AssessmentStatus, tuple[str, ...], tuple[str, ...]]:
    """Return assessment status, reason codes, and ordered ledger target statuses.

    Ledger targets are only set when verifier evidence supports a transition.
    Unknown / pending outcomes keep reservations (no release).
    Credit confirmation never skips provider confirmation on the ledger path.
    """
    reasons: list[str] = []
    if _has_conflicting_evidence(evidence):
        return "CONFLICT", ("EVIDENCE_CONFLICT",), ()

    if refund is None:
        reasons.append("REFUND_NOT_VISIBLE")
        return "WAITING", tuple(reasons), ()

    if refund.status == "PENDING":
        # Explicit: accepted/pending provider refund is not customer credit.
        reasons.append("REFUND_PENDING")
        reasons.append("CREDIT_NOT_CONFIRMED")
        return "WAITING", tuple(reasons), ()

    if refund.status == "FAILED_FINAL":
        reasons.append("REFUND_FAILED_FINAL")
        targets: list[str] = []
        if action_status != "FAILED_FINAL":
            targets.append("FAILED_FINAL")
        return "VERIFIED", tuple(reasons), tuple(targets)

    if refund.status == "PROVIDER_CONFIRMED":
        reasons.append("PROVIDER_CONFIRMED")
        targets = []
        if action_status in {"PENDING", "OUTCOME_UNKNOWN", "ESCALATED", "DISPATCHING"}:
            targets.append("PROVIDER_CONFIRMED")
        if credit is None or not credit.confirmed:
            reasons.append("CREDIT_NOT_CONFIRMED")
            return "WAITING", tuple(reasons), tuple(targets)
        reasons.append("CREDIT_CONFIRMED")
        if action_status != "CREDIT_CONFIRMED":
            if "PROVIDER_CONFIRMED" not in targets and action_status != "PROVIDER_CONFIRMED":
                targets.append("PROVIDER_CONFIRMED")
            if "CREDIT_CONFIRMED" not in targets:
                targets.append("CREDIT_CONFIRMED")
        return "VERIFIED", tuple(reasons), tuple(targets)

    reasons.append("UNKNOWN_REFUND_STATUS")
    return "WAITING", tuple(reasons), ()


def _has_conflicting_evidence(evidence: list[dict[str, Any]]) -> bool:
    return any(item.get("verification_status") == "CONFLICTING" for item in evidence)
