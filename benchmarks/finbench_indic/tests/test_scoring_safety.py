"""Acceptance: hard safety fails independently; fake/live/system scores distinct."""

from __future__ import annotations

import pytest

from sentinel_finbench.adapters.candidates import LiveModelCandidate
from sentinel_finbench.application.evaluate import evaluate_split
from sentinel_finbench.bootstrap import select_candidate
from sentinel_finbench.contracts import PeerError


def test_unsafe_candidate_fails_hard_safety_despite_model_hits(dataset):
    unsafe = evaluate_split(dataset, "val", select_candidate("unsafe"))
    baseline = evaluate_split(dataset, "val", select_candidate("recorded"))
    assert unsafe.hard_safety_pass is False
    assert unsafe.overall_status == "FAIL"
    assert unsafe.hard_safety_failures
    # Model channel can still show correct intent/amount (high average signal).
    assert any(s.mean == 1.0 and s.denominator > 0 for s in unsafe.model_scores)
    assert baseline.hard_safety_pass is True
    assert baseline.overall_status == "PASS"


class _StubContext:
    """Returns non-gold live fields so scores stay honest."""

    def propose(self, request):
        _ = request
        return {
            "outcome": "PROPOSAL",
            "original_text": "stub",
            "language": "en-IN",
            "intent": "status_inquiry",
            "reported_amount_minor": 42,
            "final_state": "OPEN",
            "proposal": {"action": "STATUS_UPDATE"},
            "financial_effects": 0,
            "unauthorized_effects": 0,
            "predicate_verified": False,
        }


def test_fake_live_recorded_and_system_scores_remain_distinct(dataset):
    fake = evaluate_split(dataset, "dev", select_candidate("fake"))
    recorded = evaluate_split(dataset, "dev", select_candidate("recorded"))
    live = evaluate_split(
        dataset,
        "dev",
        LiveModelCandidate(enabled=True, context=_StubContext()),
        evidence_mode="live-provider",
    )
    system = evaluate_split(dataset, "dev", select_candidate("system"))

    assert {s.model_label for s in fake.model_scores} == {"fake"}
    assert {s.model_label for s in recorded.model_scores} == {"recorded"}
    assert {s.model_label for s in live.model_scores} == {"live"}
    assert all(s.model_label == "system" for s in fake.system_scores)
    assert all(s.model_label == "system" for s in system.system_scores)
    # Channels are separately reported, not collapsed into one average field.
    assert "model_scores" in fake.to_dict()
    assert "system_scores" in fake.to_dict()
    assert fake.to_dict()["model_scores"][0]["model_label"] != "system"


def test_live_model_disabled_refuses_silent_fake(dataset):
    candidate = LiveModelCandidate(enabled=False)
    record = dataset.records_for_split("dev")[0]
    with pytest.raises(PeerError) as exc:
        candidate.run_scenario(record)
    assert exc.value.code == "LIVE_MODEL_DISABLED"


def test_live_model_without_peer_refuses_gold_copy(dataset):
    candidate = LiveModelCandidate(enabled=True, context=None)
    record = dataset.records_for_split("dev")[0]
    with pytest.raises(PeerError) as exc:
        candidate.run_scenario(record)
    assert exc.value.code == "LIVE_MODEL_PEER_REQUIRED"


def test_live_model_uses_peer_fields_not_expected_gold(dataset):
    candidate = LiveModelCandidate(enabled=True, context=_StubContext())
    record = dataset.records_for_split("dev")[0]
    outcome = candidate.run_scenario(record)
    assert outcome.model_label == "live"
    assert outcome.intent == "status_inquiry"
    assert outcome.amount_minor == 42
    # Peer fields win; must not silently equal gold copy of expected.
    assert (outcome.intent, outcome.amount_minor) != (
        record.expected.intent,
        record.expected.reported_amount_minor,
    )
