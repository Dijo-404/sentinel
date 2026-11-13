"""Fixture run never claims deployed evidence; malformed input fails safely."""

import json
from pathlib import Path

import pytest
from stubs.finbench import ValidFinbench
from stubs.finharness_runtime import ValidRuntime
from stubs.telemetry import ValidTelemetryExporter

from sentinel_finharness_telemetry import (
    CONTRACT_SHA256,
    HarnessTelemetryContractError,
    run,
)

ROOT = Path(__file__).resolve().parents[1]


def test_fixture_run_passes_and_labels_fixture_evidence() -> None:
    raw = json.loads((ROOT / "fixtures" / "run_input.json").read_text(encoding="utf-8"))
    report = run(raw)
    assert report.status == "PASS"
    assert report.mode == "fixture"
    assert all(a.evidence_mode == "fixture" for a in report.output_artifacts)
    assert any(a.kind == "harness-telemetry-export" for a in report.output_artifacts)
    assert any(a.kind == "dashboard-example" for a in report.output_artifacts)
    assert CONTRACT_SHA256.startswith("0c728513")


def test_real_peers_without_peers_do_not_fall_back_to_fixture_pass() -> None:
    raw = json.loads((ROOT / "fixtures" / "run_input_real_peers.json").read_text(encoding="utf-8"))
    report = run(raw)
    assert report.mode == "real-peers"
    assert report.status in ("FAIL", "UNVERIFIED")
    assert report.status != "PASS"
    assert report.output_artifacts == []


def test_real_peers_with_local_doubles_still_marks_telemetry_unverified() -> None:
    raw = json.loads((ROOT / "fixtures" / "run_input_real_peers.json").read_text(encoding="utf-8"))
    report = run(
        raw,
        telemetry_peer=ValidTelemetryExporter(),
        runtime_peer=ValidRuntime(),
        finbench_peer=ValidFinbench(),
    )
    assert report.mode == "real-peers"
    # Local doubles are not an assembled collector; telemetry stays UNVERIFIED.
    assert report.status == "UNVERIFIED"
    telemetry_check = next(c for c in report.checks if c.name == "telemetry_peer")
    assert telemetry_check.status == "UNVERIFIED"


def test_malformed_run_input_fails_safely() -> None:
    with pytest.raises(HarnessTelemetryContractError):
        run({"contract_version": "wrong", "run_id": "x", "mode": "fixture"})

    with pytest.raises(HarnessTelemetryContractError):
        run(
            {
                "contract_version": "sentinel.task-contracts.v1",
                "run_id": "x",
                "mode": "fixture",
                "input_artifacts": [],
                "parameters": {"unknown.param": True},
            }
        )
