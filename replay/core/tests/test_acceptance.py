from __future__ import annotations

from sentinel_replay.adapters.candidates import ConformingCandidate, DefectiveRetryCandidate
from sentinel_replay.adapters.production_guard import ProductionRouteBlocked
from sentinel_replay.adapters.sandbox_simulator import SandboxSimulator
from sentinel_replay.adapters.scorer import DeterministicScorer
from sentinel_replay.adapters.virtual_clock import VirtualClock
from sentinel_replay.application.service import compare_candidates, run_check
from sentinel_replay.fixtures import bundled_timeout_fixture


def test_defective_retry_fails_state_effect_assertions() -> None:
    fixture = bundled_timeout_fixture()
    outcome = DefectiveRetryCandidate().run(fixture, SandboxSimulator(), VirtualClock(fixture.seed))
    checks = DeterministicScorer().score(fixture.expected, outcome)
    by_name = {c.name: c for c in checks}
    assert outcome.refund_side_effect_count == 2
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


def test_compare_report_promotes_conforming_and_records_modes() -> None:
    report = compare_candidates(run_id="acceptance-1", mode="fixture")
    assert report.status == "PASS"
    assert report.modes.run_mode == "fixture"
    assert report.modes.seed == 42
    assert report.modes.model_mode == "fake"
    assert report.modes.production_writes_blocked is True
    assert report.modes.production_notifications_blocked is True
    assert report.modes.real_evaluation_adapter == "absent"
    assert report.modes.real_payment_provider_adapter == "absent"
    assert report.promotion is not None
    assert report.promotion.decision == "PROMOTE"
    assert report.output_artifacts[0].evidence_mode == "fixture"


def test_production_write_and_notification_routes_blocked() -> None:
    sim = SandboxSimulator()
    try:
        sim.attempt_production_write("https://api.paytm.com/v1/refunds")
        raised = False
    except ProductionRouteBlocked:
        raised = True
    assert raised
    try:
        sim.attempt_production_notification("prod://notify/customer")
        raised_n = False
    except ProductionRouteBlocked:
        raised_n = True
    assert raised_n


def test_run_check_passes() -> None:
    report = run_check()
    assert report.status == "PASS"
