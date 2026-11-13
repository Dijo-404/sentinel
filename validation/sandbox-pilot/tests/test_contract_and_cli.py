from __future__ import annotations

import json
from pathlib import Path

from sentinel_sandbox_pilot.adapters.config import load_config
from sentinel_sandbox_pilot.cli import main
from sentinel_sandbox_pilot.domain.types import CONTRACT_SHA256, CONTRACT_VERSION, PORT

ROOT = Path(__file__).resolve().parents[1]


def test_contract_snapshot_matches_baseline() -> None:
    snapshot = json.loads((ROOT / "contracts" / "sandbox-validation.v1.json").read_text())
    assert snapshot["contract_version"] == CONTRACT_VERSION
    assert snapshot["baseline_sha256"] == CONTRACT_SHA256
    assert snapshot["port"] == PORT
    assert snapshot["run_report"]["external_pilot_claimed"] is False
    assert "second_workflow" in snapshot["drivers"]
    assert "kill_switch" in snapshot["drivers"]


def test_inflight_fixture_uses_integer_money() -> None:
    fixture = json.loads((ROOT / "fixtures" / "inflight-action.json").read_text())
    assert fixture["amount_minor"] == 150000
    assert isinstance(fixture["amount_minor"], int)
    assert fixture["evidence_mode"] == "fixture"


def test_config_from_env_defaults_to_fixture(monkeypatch) -> None:
    monkeypatch.delenv("SANDBOX_PILOT_MODE", raising=False)
    monkeypatch.delenv("SANDBOX_PILOT_EXTERNAL_AUTHORIZATION", raising=False)
    cfg = load_config()
    assert cfg.mode == "fixture"
    assert cfg.contract_sha256 == CONTRACT_SHA256
    assert cfg.external_authorization is False


def test_cli_check_exits_zero(capsys) -> None:
    code = main(["check"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["status"] == "PASS"
    assert payload["external_pilot_claimed"] is False
    assert payload["pilot_verdict"] == "KIT_ONLY"


def test_cli_real_peers_without_evidence_fails(capsys) -> None:
    code = main(["run", "--mode", "real-peers", "--run-id", "cli-real"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 1
    assert payload["status"] == "FAIL"
    assert payload["external_pilot_claimed"] is False
