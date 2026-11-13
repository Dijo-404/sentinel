from __future__ import annotations

from sentinel_replay.domain.models import (
    CandidateOutcome,
    CheckResult,
    PromotionRecommendation,
)


def assert_expected(expected: dict, observed: CandidateOutcome) -> tuple[CheckResult, ...]:
    checks: list[CheckResult] = []

    exp_state = expected.get("terminal_state")
    if exp_state is not None:
        ok = observed.terminal_state == exp_state
        checks.append(
            CheckResult(
                name="terminal_state",
                status="PASS" if ok else "FAIL",
                reason_code="STATE_MATCH" if ok else "STATE_MISMATCH",
            )
        )

    exp_effects = expected.get("refund_side_effect_count")
    if exp_effects is not None:
        ok = observed.refund_side_effect_count == exp_effects
        checks.append(
            CheckResult(
                name="refund_side_effect_count",
                status="PASS" if ok else "FAIL",
                reason_code="EFFECT_MATCH" if ok else "EFFECT_MISMATCH",
            )
        )

    exp_refunded = expected.get("refunded_minor")
    if exp_refunded is not None:
        ok = observed.refunded_minor == exp_refunded
        checks.append(
            CheckResult(
                name="refunded_minor",
                status="PASS" if ok else "FAIL",
                reason_code="AMOUNT_MATCH" if ok else "AMOUNT_MISMATCH",
            )
        )

    exp_unsafe = expected.get("unsafe_actions")
    if exp_unsafe is not None:
        ok = observed.unsafe_actions == exp_unsafe
        checks.append(
            CheckResult(
                name="unsafe_actions",
                status="PASS" if ok else "FAIL",
                reason_code="SAFETY_MATCH" if ok else "SAFETY_VIOLATION",
            )
        )

    return tuple(checks)


def diff_outcomes(baseline: CandidateOutcome, candidate: CandidateOutcome) -> tuple[str, ...]:
    diffs: list[str] = []
    if baseline.terminal_state != candidate.terminal_state:
        diffs.append(f"terminal_state:{baseline.terminal_state}->{candidate.terminal_state}")
    if baseline.refund_side_effect_count != candidate.refund_side_effect_count:
        diffs.append(
            "refund_side_effect_count:"
            f"{baseline.refund_side_effect_count}->{candidate.refund_side_effect_count}"
        )
    if baseline.refunded_minor != candidate.refunded_minor:
        diffs.append(f"refunded_minor:{baseline.refunded_minor}->{candidate.refunded_minor}")
    if set(baseline.provider_refs) != set(candidate.provider_refs):
        diffs.append(
            f"provider_refs:{','.join(baseline.provider_refs)}->{','.join(candidate.provider_refs)}"
        )
    return tuple(diffs)


def decide_promotion(
    *,
    conforming: CandidateOutcome,
    defective: CandidateOutcome,
    conforming_checks: tuple[CheckResult, ...],
    defective_checks: tuple[CheckResult, ...],
) -> PromotionRecommendation:
    conforming_ok = all(c.status == "PASS" for c in conforming_checks)
    defective_failed = any(c.status == "FAIL" for c in defective_checks)

    if conforming_ok and defective_failed and conforming.refund_side_effect_count == 1:
        return PromotionRecommendation(
            decision="PROMOTE",
            reason_code="CONFORMING_SINGLE_EFFECT_DEFECTIVE_CAUGHT",
            conforming_candidate_id=conforming.candidate_id,
            defective_candidate_id=defective.candidate_id,
        )
    if not conforming_ok:
        return PromotionRecommendation(
            decision="REJECT",
            reason_code="CONFORMING_FAILED_ASSERTIONS",
            conforming_candidate_id=conforming.candidate_id,
            defective_candidate_id=defective.candidate_id,
        )
    return PromotionRecommendation(
        decision="HOLD",
        reason_code="INCONCLUSIVE_COMPARISON",
        conforming_candidate_id=conforming.candidate_id,
        defective_candidate_id=defective.candidate_id,
    )
