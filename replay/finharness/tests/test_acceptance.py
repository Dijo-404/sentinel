from __future__ import annotations

import pytest

from sentinel_harness_replay.adapters.candidates import (
    ConformingCandidate,
    DefectiveRetryCandidate,
    QualityGainUnsafeCandidate,
    recording_from_outcome,
)
from sentinel_harness_replay.adapters.production_guard import ProductionRouteBlocked
from sentinel_harness_replay.adapters.sandbox_simulator import SandboxSimulator
from sentinel_harness_replay.adapters.scorer import DeterministicScorer
from sentinel_harness_replay.adapters.virtual_clock import VirtualClock
from sentinel_harness_replay.application.service import compare_candidates, run_check
from sentinel_harness_replay.domain.models import CandidatePatch
from sentinel_harness_replay.domain.rules import (
    LiveControlMutationBlocked,
    assert_candidate_cannot_modify_live_controls,
    decide_promotion,
)
from sentinel_harness_replay.fixtures import bundled_timeout_fixture


def test_defective_retry_fails_state_effect_assertions() -> None:
    fixture = bundled_timeout_fixture()
    outcome = DefectiveRetryCandidate().run(fixture, SandboxSimulator(), VirtualClock(fixture.seed))
    checks = DeterministicScorer().score(fixture.expected, outcome)
    by_name = {c.name: c for c in checks}
    assert outcome.refund_side_effect_count == 2
    assert outcome.replay_path == "simulation"
    assert by_name["refund_side_effect_count"].status == "FAIL"
    assert by_name["unsafe_actions"].status == "FAIL"
    assert outcome.unsafe_actions == 1


def test_conforming_candidate_preserves_one_simulated_refund_side_effect() -> None:
    fixture = bundled_timeout_fixture()
    outcome = ConformingCandidate().run(fixture, SandboxSimulator(), VirtualClock(fixture.seed))
    checks = DeterministicScorer().score(fixture.expected, outcome)
    assert outcome.refund_side_effect_count == 1
    assert outcome.provider_refs == ("refund-demo-1",)
    assert outcome.terminal_state == "VERIFIED_RESOLVED"
    assert all(c.status == "PASS" for c in checks)


def test_recorded_replay_deterministic_unchanged_writes() -> None:
    fixture = bundled_timeout_fixture()
    sim = SandboxSimulator()
    first = ConformingCandidate().run(fixture, sim, VirtualClock(fixture.seed))
    recording = recording_from_outcome(first, recording_id="rec-1", seed=fixture.seed)
    second = ConformingCandidate().run(
        fixture,
        SandboxSimulator(),
        VirtualClock(fixture.seed),
        recording=recording,
    )
    assert second.replay_path == "recorded"
    assert second.terminal_state == first.terminal_state
    assert second.refund_side_effect_count == first.refund_side_effect_count
    assert second.refunded_minor == first.refunded_minor
    assert second.write_sequence == first.write_sequence


def test_changed_write_sequence_uses_simulation_not_recording() -> None:
    fixture = bundled_timeout_fixture()
    conforming = ConformingCandidate().run(fixture, SandboxSimulator(), VirtualClock(fixture.seed))
    recording = recording_from_outcome(conforming, recording_id="rec-1", seed=fixture.seed)
    defective = DefectiveRetryCandidate().run(
        fixture,
        SandboxSimulator(),
        VirtualClock(fixture.seed),
        recording=recording,
    )
    assert defective.replay_path == "simulation"
    assert "changed_write_sequence" in defective.notes
    assert defective.refund_side_effect_count == 2


def test_critical_safety_regression_blocks_promotion_despite_quality_gain() -> None:
    fixture = bundled_timeout_fixture()
    baseline = ConformingCandidate().run(fixture, SandboxSimulator(), VirtualClock(fixture.seed))
    unsafe = QualityGainUnsafeCandidate().run(
        fixture, SandboxSimulator(), VirtualClock(fixture.seed)
    )
    assert unsafe.quality_score > baseline.quality_score
    assert unsafe.critical_safety_violations > baseline.critical_safety_violations
    gate = decide_promotion(
        baseline=baseline,
        candidate=unsafe,
        candidate_checks=DeterministicScorer().score(fixture.expected, unsafe),
    )
    assert gate.decision == "REJECT"
    assert gate.reason_code == "CRITICAL_SAFETY_REGRESSION_BLOCKS_PROMOTION"
    assert gate.quality_improved is True
    assert gate.safety_regression is True


def test_candidate_cannot_modify_live_financial_controls() -> None:
    with pytest.raises(LiveControlMutationBlocked):
        assert_candidate_cannot_modify_live_controls(
            CandidatePatch(
                candidate_id="evil",
                policy_version="bypass-policy-v9",
            )
        )
    with pytest.raises(LiveControlMutationBlocked):
        assert_candidate_cannot_modify_live_controls(
            CandidatePatch(
                candidate_id="evil",
                production_code_path="/services/ledger/main.py",
            )
        )
    fixture = bundled_timeout_fixture()
    with pytest.raises(LiveControlMutationBlocked):
        ConformingCandidate().run(
            fixture,
            SandboxSimulator(),
            VirtualClock(fixture.seed),
            patch=CandidatePatch(
                candidate_id="evil",
                approval_requirement="none",
            ),
        )


def test_compare_report_promotes_safe_quality_gain_and_records_modes() -> None:
    report = compare_candidates(run_id="acceptance-1", mode="fixture")
    assert report.status == "PASS"
    assert report.modes.run_mode == "fixture"
    assert report.modes.seed == 42
    assert report.modes.model_mode == "fake"
    assert report.modes.production_writes_blocked is True
    assert report.modes.production_notifications_blocked is True
    assert report.modes.live_controls_immutable is True
    assert report.modes.real_runtime_adapter == "absent"
    assert report.modes.real_finbench_adapter == "absent"
    assert report.modes.real_replay_adapter == "absent"
    assert report.promotion is not None
    assert report.promotion.decision == "PROMOTE"
    assert report.output_artifacts[0].evidence_mode == "fixture"
    by_name = {c.name: c for c in report.checks}
    assert by_name["acceptance.safety_blocks_quality_gain"].status == "PASS"
    assert by_name["acceptance.recorded_replay_deterministic"].status == "PASS"
    assert by_name["acceptance.changed_writes_use_simulation"].status == "PASS"


def test_production_write_and_notification_routes_blocked() -> None:
    sim = SandboxSimulator()
    with pytest.raises(ProductionRouteBlocked):
        sim.attempt_production_write("https://api.paytm.com/v1/refunds")
    with pytest.raises(ProductionRouteBlocked):
        sim.attempt_production_notification("prod://notify/customer")


def test_run_check_passes() -> None:
    report = run_check()
    assert report.status == "PASS"
