"""Four-journey runner against local reference peers."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_core_assembly.adapters.reference import ReferenceBundle
from sentinel_core_assembly.application.assembly import run_assembly
from sentinel_core_assembly.domain.journeys import evaluate_journey, expectation_for
from sentinel_core_assembly.domain.types import (
    AUTHORITY_FIXTURE_PATH,
    CONTRACT_SHA256,
    CONTRACT_VERSION,
    FIXTURE_PATH,
    JOURNEYS,
    RunInput,
)

# Fixture / authority-fixture path labels — never live-provider rails.
_HONEST_FIXTURE_PATHS = frozenset({FIXTURE_PATH, AUTHORITY_FIXTURE_PATH})

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_all_journeys_pass_with_local_reference_peers() -> None:
    peers = ReferenceBundle()
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="fixture-all-journeys",
            mode="fixture",
        ),
        peers,
    )
    assert report.status == "PASS"
    assert report.assembled_mvp_claimed is False
    assert report.mode == "fixture"
    assert report.path == "browser-to-credit-fixture"
    assert report.path in _HONEST_FIXTURE_PATHS
    assert report.path != "live-provider"
    assert report.payment_provider == "simulator"
    assert report.as_dict()["payment_provider"] == "simulator"
    assert report.sn009_authority_exercised is True
    names = {c.name for c in report.checks if c.name.startswith("journey.")}
    assert names == {f"journey.{j}" for j in JOURNEYS}
    assert all(c.status == "PASS" for c in report.checks if c.name.startswith("journey."))


def test_browser_to_credit_fixture_exercises_authority_stages() -> None:
    outcome = ReferenceBundle().run_browser_to_credit()
    assert outcome["sn009_authority_exercised"] is True
    assert outcome["customer_closed"] is True
    assert outcome["credit_confirmed"] is True
    assert set(outcome["stages"]) >= {
        "intake",
        "proposal",
        "approval",
        "reservation",
        "dispatcher",
        "verifier",
        "closure",
    }


def test_duplicate_approval_deny_fixture() -> None:
    outcome = ReferenceBundle().run_duplicate_approval_deny()
    assert outcome["duplicate_approval_denied"] is True
    assert outcome["refunded_minor"] == 0
    assert outcome["sn009_authority_exercised"] is True
    assert outcome["terminal_state"] == "NEEDS_HUMAN"


def test_duplicate_payment_includes_150000_timeout_and_credit_recovery() -> None:
    peers = ReferenceBundle()
    outcome = peers.run_duplicate_payment()
    assert outcome["amount_minor"] == 150_000
    assert outcome["refunded_minor"] == 150_000
    assert outcome["refund_side_effect_count"] == 1
    assert outcome["timeout_recovered"] is True
    assert outcome["credit_confirmed"] is True
    assert outcome["terminal_state"] == "VERIFIED_RESOLVED"
    assert outcome["approval_required"] is True

    fixture = json.loads((FIXTURES / "duplicate_payment.json").read_text(encoding="utf-8"))
    assert fixture["expected"]["refunded_minor"] == 150_000
    assert fixture["baseline_sha256"] == CONTRACT_SHA256
    assert fixture["evidence_mode"] == "fixture"


def test_fixture_pass_never_claims_mvp_release() -> None:
    report = run_assembly(
        RunInput(contract_version=CONTRACT_VERSION, run_id="no-mvp", mode="fixture"),
        ReferenceBundle(),
    )
    assert report.status == "PASS"
    assert report.assembled_mvp_claimed is False
    mvp = next(c for c in report.checks if c.name == "assembly.mvp_claim")
    assert mvp.reason_code == "HARNESS_PASS_IS_NOT_MVP_RELEASE"
    assert report.output_artifacts[0].evidence_mode == "fixture"
    assert report.payment_provider == "simulator"
    assert report.path in _HONEST_FIXTURE_PATHS
    assert report.path != "live-provider"


def test_fixture_report_honesty_labels_for_authority_money_path() -> None:
    """Fixture assembly must label simulator + authority path; never live-provider."""
    report = run_assembly(
        RunInput(
            contract_version=CONTRACT_VERSION,
            run_id="honesty-fixture",
            mode="fixture",
            parameters={"journeys": "browser_to_credit"},
        ),
        ReferenceBundle(),
    )
    payload = report.as_dict()
    assert report.status == "PASS"
    assert payload["payment_provider"] == "simulator"
    assert payload["path"] == AUTHORITY_FIXTURE_PATH
    assert payload["path"] != "live-provider"
    assert payload["sn009_authority_exercised"] is True
    assert payload["assembled_mvp_claimed"] is False


def test_duplicate_payment_fails_when_timeout_recovery_missing() -> None:
    outcome = {
        "terminal_state": "VERIFIED_RESOLVED",
        "refunded_minor": 150_000,
        "refund_side_effect_count": 1,
        "approval_required": True,
        "unsafe_actions": 0,
        "amount_minor": 150_000,
        "timeout_recovered": False,
        "credit_confirmed": True,
    }
    result = evaluate_journey(outcome, expectation_for("duplicate_payment"))
    assert result.status == "FAIL"
    assert result.reason_code == "TIMEOUT_RECOVERY_MISSING"
