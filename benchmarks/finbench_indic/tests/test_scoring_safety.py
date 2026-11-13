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


def test_fake_live_recorded_and_system_scores_remain_distinct(dataset):
    fake = evaluate_split(dataset, "dev", select_candidate("fake"))
    recorded = evaluate_split(dataset, "dev", select_candidate("recorded"))
    live = evaluate_split(dataset, "dev", LiveModelCandidate(enabled=True))
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
