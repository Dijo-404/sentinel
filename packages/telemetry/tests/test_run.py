"""RunInput/RunReport contract entry and CLI-facing checks."""

import json
from pathlib import Path

import pytest

from sentinel_telemetry import RunInput, TelemetryContractError, run
from sentinel_telemetry.contracts import CONTRACT_SHA256, CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[1]


def test_fixture_run_passes_acceptance_checks() -> None:
    payload = json.loads((ROOT / "fixtures" / "run_input.json").read_text(encoding="utf-8"))
    report = run(payload)
    assert report.contract_version == CONTRACT_VERSION
    assert report.mode == "fixture"
    assert report.status == "PASS"
    names = {check.name: check.status for check in report.checks}
    assert names["correlation_export"] == "PASS"
    assert names["timeout_retry_events"] == "PASS"
    assert names["otel_hooks"] == "PASS"
    assert names["redaction_bounds"] == "PASS"
    assert names["audit_isolation"] == "PASS"
    assert any(a.kind == "telemetry-export" for a in report.output_artifacts)
    assert any(a.kind == "collector-example" for a in report.output_artifacts)
    assert any(a.kind == "dashboard-example" for a in report.output_artifacts)


def test_real_peers_unverified_without_assembled_collector() -> None:
    payload = json.loads(
        (ROOT / "fixtures" / "run_input_real_peers.json").read_text(encoding="utf-8")
    )
    report = run(payload)
    assert report.status == "UNVERIFIED"
    assert report.checks[0].reason_code == "REAL_PEER_COLLECTOR_NOT_ASSEMBLED"


def test_unsupported_parameter_fails_explicitly() -> None:
    with pytest.raises(TelemetryContractError):
        run(
            {
                "contract_version": CONTRACT_VERSION,
                "run_id": "bad-1",
                "mode": "fixture",
                "input_artifacts": [],
                "parameters": {"telemetry.unknown_required": True},
            }
        )


def test_contract_version_mismatch() -> None:
    with pytest.raises(TelemetryContractError):
        RunInput.from_dict(
            {
                "contract_version": "other",
                "run_id": "x",
                "mode": "fixture",
                "input_artifacts": [],
                "parameters": {},
            }
        )


def test_contract_hash_pinned() -> None:
    assert CONTRACT_SHA256 == ("0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa")


def test_contract_snapshot_present() -> None:
    snapshot = ROOT / "contracts" / "telemetry.v1.json"
    data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert data["port"] == "telemetry.v1"
    assert data["baseline_sha256"] == CONTRACT_SHA256
