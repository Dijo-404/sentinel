from __future__ import annotations

from sentinel_evaluation.domain.models import CandidateObservation, EvalFixture


class ConformingCandidate:
    """Safe local double: matches expected outcomes without safety violations."""

    candidate_id = "local-conforming"
    model_mode = "fake"

    def run(self, fixture: EvalFixture) -> CandidateObservation:
        expected = fixture.expected
        return CandidateObservation(
            terminal_state=expected.terminal_state,
            refund_side_effect_count=expected.refund_side_effect_count,
            refunded_minor=expected.refunded_minor,
            currency=fixture.currency,
            actions=fixture.allowed_actions[:1] or ("STATUS_UPDATE",),
            accessed_tenant_id=fixture.tenant_id,
            claims_credit_confirmed=fixture.credit_actually_confirmed
            and expected.terminal_state == "VERIFIED_RESOLVED",
            approval_obtained=expected.approval_required or True,
            model_mode=self.model_mode,
        )


class UnauthorizedActionCandidate:
    candidate_id = "local-unsafe-unauthorized"
    model_mode = "fake"

    def run(self, fixture: EvalFixture) -> CandidateObservation:
        base = ConformingCandidate().run(fixture)
        return CandidateObservation(
            terminal_state=base.terminal_state,
            refund_side_effect_count=base.refund_side_effect_count,
            refunded_minor=base.refunded_minor,
            currency=base.currency,
            actions=("FORGE_APPROVAL", "REQUEST_REFUND"),
            accessed_tenant_id=base.accessed_tenant_id,
            claims_credit_confirmed=base.claims_credit_confirmed,
            approval_obtained=True,
            model_mode=self.model_mode,
        )


class OverRefundCandidate:
    candidate_id = "local-unsafe-over-refund"
    model_mode = "fake"

    def run(self, fixture: EvalFixture) -> CandidateObservation:
        base = ConformingCandidate().run(fixture)
        return CandidateObservation(
            terminal_state=base.terminal_state,
            refund_side_effect_count=1,
            refunded_minor=fixture.eligible_refund_minor + 1,
            currency=base.currency,
            actions=base.actions,
            accessed_tenant_id=base.accessed_tenant_id,
            claims_credit_confirmed=base.claims_credit_confirmed,
            approval_obtained=True,
            model_mode=self.model_mode,
        )


class CrossTenantCandidate:
    candidate_id = "local-unsafe-cross-tenant"
    model_mode = "fake"

    def run(self, fixture: EvalFixture) -> CandidateObservation:
        base = ConformingCandidate().run(fixture)
        return CandidateObservation(
            terminal_state=base.terminal_state,
            refund_side_effect_count=base.refund_side_effect_count,
            refunded_minor=base.refunded_minor,
            currency=base.currency,
            actions=base.actions,
            accessed_tenant_id="tenant-other-unauthorized",
            claims_credit_confirmed=base.claims_credit_confirmed,
            approval_obtained=True,
            model_mode=self.model_mode,
        )


class DuplicateEffectCandidate:
    candidate_id = "local-unsafe-duplicate-effect"
    model_mode = "fake"

    def run(self, fixture: EvalFixture) -> CandidateObservation:
        base = ConformingCandidate().run(fixture)
        return CandidateObservation(
            terminal_state=base.terminal_state,
            refund_side_effect_count=2,
            refunded_minor=base.refunded_minor,
            currency=base.currency,
            actions=base.actions,
            accessed_tenant_id=base.accessed_tenant_id,
            claims_credit_confirmed=base.claims_credit_confirmed,
            approval_obtained=True,
            model_mode=self.model_mode,
        )


class FalseCreditCandidate:
    candidate_id = "local-unsafe-false-credit"
    model_mode = "fake"

    def run(self, fixture: EvalFixture) -> CandidateObservation:
        base = ConformingCandidate().run(fixture)
        return CandidateObservation(
            terminal_state=base.terminal_state,
            refund_side_effect_count=base.refund_side_effect_count,
            refunded_minor=base.refunded_minor,
            currency=base.currency,
            actions=base.actions,
            accessed_tenant_id=base.accessed_tenant_id,
            claims_credit_confirmed=True,
            approval_obtained=base.approval_obtained,
            model_mode=self.model_mode,
        )


CANDIDATES: dict[str, type] = {
    "conforming": ConformingCandidate,
    "unauthorized": UnauthorizedActionCandidate,
    "over_refund": OverRefundCandidate,
    "cross_tenant": CrossTenantCandidate,
    "duplicate_effect": DuplicateEffectCandidate,
    "false_credit": FalseCreditCandidate,
}


def build_candidate(name: str):
    try:
        cls = CANDIDATES[name]
    except KeyError as exc:
        known = ", ".join(sorted(CANDIDATES))
        raise ValueError(f"Unknown candidate {name!r}; known: {known}") from exc
    return cls()
