"""Local candidate adapters. Fake/live/recorded labels stay distinct."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sentinel_finbench.contracts import CONTRACT_VERSION, ModelLabel, PeerError
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


def _outcome_from_context(
    record: ScenarioRecord,
    raw: Mapping[str, Any],
) -> CandidateOutcome:
    """Map indic-context / live peer fields — never copy record.expected as live gold."""
    proposal = raw.get("proposal") if isinstance(raw.get("proposal"), Mapping) else {}
    action = proposal.get("action") if isinstance(proposal, Mapping) else None
    outcome = raw.get("outcome")
    intent = raw.get("intent")
    if not isinstance(intent, str):
        intent = None
    amount = raw.get("reported_amount_minor")
    if amount is not None and not isinstance(amount, int):
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            amount = None
    final_state = raw.get("final_state")
    if not isinstance(final_state, str) or not final_state:
        final_state = "OPEN"
    abstained = outcome in {"NEEDS_INPUT", "ESCALATE"} or action in {
        None,
        "STATUS_UPDATE",
        "NEEDS_INPUT",
    }
    financial_effects = raw.get("financial_effects", 0)
    if not isinstance(financial_effects, int):
        financial_effects = 0
    unauthorized = raw.get("unauthorized_effects", 0)
    if not isinstance(unauthorized, int):
        unauthorized = 0
    confirmed = raw.get("confirmed_total_minor")
    if confirmed is not None and not isinstance(confirmed, int):
        confirmed = None
    predicate = raw.get("predicate_verified")
    if not isinstance(predicate, bool):
        predicate = final_state in {"RESOLVED", "VERIFIED_RESOLVED"}
    proposal_type = action if isinstance(action, str) else None
    return CandidateOutcome(
        scenario_id=record.scenario_id,
        intent=intent,
        amount_minor=amount,
        proposal_type=proposal_type,
        abstained=abstained,
        final_state=final_state,
        financial_effects=financial_effects,
        unauthorized_effects=unauthorized,
        confirmed_total_minor=confirmed,
        predicate_verified=predicate,
        model_label="live",
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
    """Opt-in live path. Requires an injected context peer; never copies gold as live."""

    candidate_id = "candidate-live-model-v1"

    def __init__(self, *, enabled: bool = False, context: Any | None = None) -> None:
        self._enabled = enabled
        self._context = context

    def run_scenario(self, record: ScenarioRecord) -> CandidateOutcome:
        if not self._enabled:
            raise PeerError(
                "finbench.v1",
                "LIVE_MODEL_DISABLED",
                "live model mode requires explicit enable; refusing silent fake fallback",
            )
        if self._context is None:
            raise PeerError(
                "finbench.v1",
                "LIVE_MODEL_PEER_REQUIRED",
                "live model requires an injected context peer; refusing gold-copy fake live",
            )
        raw = self._context.propose(
            {
                "case": {
                    "contract_version": CONTRACT_VERSION,
                    "scenario_id": record.scenario_id,
                },
                "input": {
                    "original_text": record.text,
                    "language": record.language,
                },
                "evidence": [],
            }
        )
        if not isinstance(raw, Mapping):
            raise PeerError("finbench.v1", "MALFORMED", "live peer returned non-object")
        return _outcome_from_context(record, raw)


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
