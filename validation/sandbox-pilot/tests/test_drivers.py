from __future__ import annotations

from sentinel_sandbox_pilot.adapters.reference import ReferenceBundle
from sentinel_sandbox_pilot.application.validation import run_validation
from sentinel_sandbox_pilot.domain.types import (
    CONTRACT_VERSION,
    DEMO_ACTION_ID,
    DEMO_PROVIDER_REF,
    DEMO_RUNTIME_PIN,
    RunInput,
)


def _fixture_run(**params: object) -> RunInput:
    return RunInput(
        contract_version=CONTRACT_VERSION,
        run_id="drivers-test",
        mode="fixture",
        parameters={"component_version": "0.1.0", **params},  # type: ignore[arg-type]
    )


def test_all_drivers_pass_with_local_reference_peers() -> None:
    report = run_validation(_fixture_run(), ReferenceBundle())
    assert report.status == "PASS"
    assert report.external_pilot_claimed is False
    assert report.pilot_verdict == "KIT_ONLY"
    driver_checks = [c for c in report.checks if c.name.startswith("driver.")]
    assert len(driver_checks) == 6
    assert all(c.status == "PASS" for c in driver_checks)


def test_restart_preserves_action_identity_and_reconciles() -> None:
    peers = ReferenceBundle()
    outcome = peers.run_restart()
    assert outcome["action_id"] == DEMO_ACTION_ID
    assert outcome["provider_ref"] == DEMO_PROVIDER_REF
    assert outcome["minted_second_refund"] is False
    assert outcome["reconciled"] is True


def test_restore_preserves_runtime_pin() -> None:
    peers = ReferenceBundle()
    outcome = peers.run_restore()
    assert outcome["restore_ok"] is True
    assert outcome["action_id"] == DEMO_ACTION_ID
    assert outcome["provider_ref"] == DEMO_PROVIDER_REF
    assert outcome["runtime_pin"] == DEMO_RUNTIME_PIN


def test_failed_restore_cannot_pass() -> None:
    report = run_validation(
        _fixture_run(drivers="restore", **{"sandbox_validation.fail_restore": True}),
        ReferenceBundle(),
    )
    assert report.status == "FAIL"
    assert any(c.reason_code == "RESTORE_FAILED" for c in report.checks)
    assert report.external_pilot_claimed is False


def test_kill_switch_blocks_writes_keeps_reconciliation() -> None:
    outcome = ReferenceBundle().run_kill_switch()
    assert outcome["new_writes_blocked"] is True
    assert outcome["reconciliation_continued"] is True
    assert outcome["action_id"] == DEMO_ACTION_ID


def test_rollback_keeps_inflight_pin_routes_new_cases() -> None:
    outcome = ReferenceBundle().run_rollback()
    assert outcome["new_cases_routed_to"] == "runtime-b"
    assert outcome["inflight_runtime_pin"] == DEMO_RUNTIME_PIN
    assert outcome["provider_ref"] == DEMO_PROVIDER_REF


def test_fixture_pass_never_claims_external_pilot() -> None:
    report = run_validation(
        _fixture_run(**{"sandbox_validation.claim_external_pilot": True}),
        ReferenceBundle(),
    )
    assert report.status == "FAIL"
    assert report.pilot_verdict == "NOT_AUTHORIZED"
    assert report.external_pilot_claimed is False
