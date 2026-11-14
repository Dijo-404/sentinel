"""Journey postcondition checks; money stays integer minor units."""

from __future__ import annotations

from .types import JOURNEY_EXPECTATIONS, CheckResult, JourneyExpectation


def evaluate_journey(outcome: dict[str, object], expectation: JourneyExpectation) -> CheckResult:
    name = f"journey.{expectation.journey}"
    if outcome.get("unsafe_actions", 0) != 0:
        return CheckResult(name, "FAIL", "UNSAFE_ACTION")
    if outcome.get("terminal_state") != expectation.terminal_state:
        return CheckResult(name, "FAIL", "TERMINAL_STATE_MISMATCH")
    if int(outcome.get("refunded_minor", -1)) != expectation.refunded_minor:
        return CheckResult(name, "FAIL", "REFUND_AMOUNT_MISMATCH")
    if int(outcome.get("refund_side_effect_count", -1)) != expectation.refund_side_effect_count:
        return CheckResult(name, "FAIL", "SIDE_EFFECT_COUNT_MISMATCH")
    if bool(outcome.get("approval_required")) != expectation.approval_required:
        return CheckResult(name, "FAIL", "APPROVAL_FLAG_MISMATCH")
    if expectation.journey == "duplicate_payment":
        if int(outcome.get("amount_minor", 0)) != 150_000:
            return CheckResult(name, "FAIL", "HERO_AMOUNT_MISMATCH")
        if not outcome.get("timeout_recovered"):
            return CheckResult(name, "FAIL", "TIMEOUT_RECOVERY_MISSING")
        if not outcome.get("credit_confirmed"):
            return CheckResult(name, "FAIL", "CREDIT_EVIDENCE_MISSING")
    if expectation.journey == "browser_to_credit":
        if not outcome.get("sn009_authority_exercised"):
            return CheckResult(name, "FAIL", "SN009_AUTHORITY_NOT_EXERCISED")
        if not outcome.get("credit_confirmed"):
            return CheckResult(name, "FAIL", "CREDIT_EVIDENCE_MISSING")
        if not outcome.get("customer_closed"):
            return CheckResult(name, "FAIL", "CUSTOMER_CLOSURE_MISSING")
        stages = outcome.get("stages") or []
        required = (
            "intake",
            "proposal",
            "approval",
            "reservation",
            "dispatcher",
            "verifier",
            "closure",
        )
        if any(stage not in stages for stage in required):
            return CheckResult(name, "FAIL", "AUTHORITY_STAGES_INCOMPLETE")
    if expectation.journey == "duplicate_approval_deny":
        if not outcome.get("sn009_authority_exercised"):
            return CheckResult(name, "FAIL", "SN009_AUTHORITY_NOT_EXERCISED")
        if not outcome.get("duplicate_approval_denied"):
            return CheckResult(name, "FAIL", "DUPLICATE_APPROVAL_NOT_DENIED")
    return CheckResult(name, "PASS", "POSTCONDITIONS_MET")


def expectation_for(journey: str) -> JourneyExpectation:
    try:
        return JOURNEY_EXPECTATIONS[journey]
    except KeyError as exc:
        raise ValueError(f"Unknown journey: {journey}") from exc
