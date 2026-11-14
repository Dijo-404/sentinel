"""Pure recovery/dispatch decisions. Never invents provider references."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sentinel_dispatcher.domain.types import ActionState, ProviderCapabilities, Refund


@dataclass(frozen=True)
class OutcomeDecision:
    status: ActionState
    reason_code: str
    may_resubmit: bool = False


def after_accepted_refund(refund: Refund) -> OutcomeDecision:
    if refund.status == "FAILED_FINAL":
        # Dispatcher may only report PENDING / OUTCOME_UNKNOWN / ESCALATED.
        # Provider FAILED_FINAL is escalated with reservation retained; ledger alone
        # may later apply authoritative FAILED_FINAL release.
        return OutcomeDecision(status="ESCALATED", reason_code="PROVIDER_FAILED_FINAL")
    if refund.status == "PROVIDER_CONFIRMED":
        # Dispatcher acceptance is still pending verification; ledger PENDING is correct.
        return OutcomeDecision(status="PENDING", reason_code="PROVIDER_ACCEPTED")
    return OutcomeDecision(status="PENDING", reason_code="PROVIDER_ACCEPTED")


def after_provider_timeout(capabilities: ProviderCapabilities) -> OutcomeDecision:
    """Timeout after a possible commit: preserve reservation, never mint a new reference."""
    if capabilities.status_lookup or capabilities.same_key_retry:
        return OutcomeDecision(
            status="OUTCOME_UNKNOWN",
            reason_code="PROVIDER_TIMEOUT_RECONCILE",
            may_resubmit=capabilities.same_key_retry,
        )
    return OutcomeDecision(
        status="ESCALATED",
        reason_code="PROVIDER_AMBIGUOUS_NO_SAFE_RETRY",
        may_resubmit=False,
    )


def after_lookup(
    *,
    capabilities: ProviderCapabilities,
    refund: Refund | None,
    lookup_not_found: bool,
) -> OutcomeDecision:
    if refund is not None:
        return after_accepted_refund(refund)
    if lookup_not_found:
        # 404 is not proof the ambiguous write failed.
        if capabilities.same_key_retry:
            return OutcomeDecision(
                status="OUTCOME_UNKNOWN",
                reason_code="LOOKUP_NOT_FOUND_SAFE_RETRY",
                may_resubmit=True,
            )
        return OutcomeDecision(
            status="ESCALATED",
            reason_code="LOOKUP_AMBIGUOUS_PRESERVE_RESERVATION",
            may_resubmit=False,
        )
    return OutcomeDecision(
        status="ESCALATED",
        reason_code="LOOKUP_UNAVAILABLE_PRESERVE_RESERVATION",
        may_resubmit=False,
    )


RecoveryAction = Literal["noop", "lookup", "resubmit_same_ref", "escalate"]


@dataclass(frozen=True)
class RecoveryPlan:
    action: RecoveryAction
    reason_code: str


def plan_recovery(
    *,
    phase: str,
    capabilities: ProviderCapabilities,
    outcome_status: str | None,
) -> RecoveryPlan:
    # Terminal only after reconcile finished (or no-safe-path escalate / lease loss).
    if phase in {"OUTCOME_REPORTED", "ESCALATED", "SUPERSEDED"}:
        return RecoveryPlan(action="noop", reason_code="ALREADY_TERMINAL")
    # Crash-after-timeout / peer-error: SUBMITTED|RECONCILING stay incomplete until lookup/retry.
    if phase in {"SUBMITTED", "RECONCILING"}:
        if capabilities.status_lookup:
            return RecoveryPlan(action="lookup", reason_code="RECOVER_LOOKUP_ORIGINAL_REF")
        if capabilities.same_key_retry:
            return RecoveryPlan(action="resubmit_same_ref", reason_code="RECOVER_SAME_KEY_RETRY")
        return RecoveryPlan(action="escalate", reason_code="RECOVER_ESCALATE_NO_SAFE_PATH")
    if phase == "CLAIMED":
        # Crash before confirmed provider accept: still only ever use original provider_ref.
        if capabilities.same_key_retry or capabilities.status_lookup:
            return RecoveryPlan(
                action="resubmit_same_ref" if capabilities.same_key_retry else "lookup",
                reason_code="RECOVER_CLAIMED_ORIGINAL_REF",
            )
        return RecoveryPlan(action="escalate", reason_code="RECOVER_CLAIMED_ESCALATE")
    if outcome_status == "OUTCOME_UNKNOWN":
        return RecoveryPlan(action="lookup", reason_code="RECOVER_UNKNOWN")
    return RecoveryPlan(action="escalate", reason_code="RECOVER_UNKNOWN_PHASE")
