"""Local candidate adapters. Fake/live/recorded labels stay distinct."""

from __future__ import annotations

from sentinel_finbench.contracts import ModelLabel, PeerError
from sentinel_finbench.domain.dataset import ScenarioRecord
from sentinel_finbench.domain.scoring import CandidateOutcome


def _gold_outcome(record: ScenarioRecord, *, model_label: ModelLabel) -> CandidateOutcome:
    expected = record.expected
    proposal = expected.allowed_proposal_types[0] if expected.allowed_proposal_types else None
    return CandidateOutcome(
        scenario_id=record.scenario_id,
        intent=expected.intent,
        amount_minor=expected.reported_amount_minor,
        proposal_type=proposal,
        abstained=False,
        final_state=expected.final_state,
        financial_effects=min(1, expected.max_financial_effects),
        unauthorized_effects=0,
        confirmed_total_minor=expected.confirmed_total_minor,
        predicate_verified=expected.final_state in {"RESOLVED", "VERIFIED_RESOLVED"},
        model_label=model_label,
    )


class RecordedBaselineCandidate:
    """Deterministic recorded-output baseline (regression)."""

    candidate_id = "baseline-recorded-v1"

    def run_scenario(self, record: ScenarioRecord) -> CandidateOutcome:
        return _gold_outcome(record, model_label="recorded")


class FakeModelCandidate:
    """Local fake inference: follows gold intent/amount without live network."""

    candidate_id = "candidate-fake-model-v1"

    def run_scenario(self, record: ScenarioRecord) -> CandidateOutcome:
        return _gold_outcome(record, model_label="fake")


class LiveModelCandidate:
    """Opt-in live path. Without explicit enable, refuses rather than faking success."""

    candidate_id = "candidate-live-model-v1"

    def __init__(self, *, enabled: bool = False) -> None:
        self._enabled = enabled

    def run_scenario(self, record: ScenarioRecord) -> CandidateOutcome:
        if not self._enabled:
            raise PeerError(
                "finbench.v1",
                "LIVE_MODEL_DISABLED",
                "live model mode requires explicit enable; refusing silent fake fallback",
            )
        # Even when enabled in this standalone kit, outcomes stay synthetic-labeled live.
        return _gold_outcome(record, model_label="live")


class DeterministicSystemCandidate:
    """System-path candidate: correct ledger/state assertions, recorded model label."""

    candidate_id = "candidate-deterministic-system-v1"

    def run_scenario(self, record: ScenarioRecord) -> CandidateOutcome:
        return _gold_outcome(record, model_label="recorded")


class UnsafeRegressionCandidate:
    """Fault demonstration: high average-looking model fields but unauthorized effects."""

    candidate_id = "candidate-unsafe-regression-v1"

    def run_scenario(self, record: ScenarioRecord) -> CandidateOutcome:
        expected = record.expected
        proposal = expected.allowed_proposal_types[0] if expected.allowed_proposal_types else None
        return CandidateOutcome(
            scenario_id=record.scenario_id,
            intent=expected.intent,
            amount_minor=expected.reported_amount_minor,
            proposal_type=proposal,
            abstained=False,
            final_state=expected.final_state,
            financial_effects=expected.max_financial_effects + 1,
            unauthorized_effects=expected.max_unauthorized_effects + 1,
            confirmed_total_minor=expected.confirmed_total_minor,
            predicate_verified=True,
            model_label="fake",
        )
