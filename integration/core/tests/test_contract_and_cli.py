"""Contract snapshot, config, and CLI self-check."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_core_assembly import CONTRACT_SHA256, CONTRACT_VERSION, PORT
from sentinel_core_assembly.adapters.config import AssemblyConfig
from sentinel_core_assembly.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_contract_snapshot_matches_baseline() -> None:
    raw = (ROOT / "contracts" / "core-assembly.v1.json").read_text(encoding="utf-8")
    snapshot = json.loads(raw)
    assert snapshot["contract_version"] == CONTRACT_VERSION
    assert snapshot["baseline_sha256"] == CONTRACT_SHA256
    assert snapshot["port"] == PORT
    assert snapshot["run_report"]["assembled_mvp_claimed"] is False
    assert set(snapshot["journeys"]) == {
        "pending",
        "merchant_mismatch",
        "duplicate_payment",
        "refund_pending",
        "browser_to_credit",
        "duplicate_approval_deny",
    }
    assert snapshot["compatibility"]["real_peer_fallback"] == "none"


def test_config_from_env_defaults_to_fixture() -> None:
    cfg = AssemblyConfig.from_env({})
    assert cfg.mode == "fixture"
    assert cfg.contract_sha256 == CONTRACT_SHA256
    assert cfg.missing_endpoints() == (
        "case-api.v1",
        "workflow.v1",
        "action-ledger.v1",
        "dispatcher.v1",
        "verifier.v1",
        "payment-provider.v1",
        "web-shell.v1",
    )


def test_cli_check_exits_zero(capsys) -> None:
    code = main(["check", "--run-id", "cli-self-test"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["mode"] == "fixture"
    assert payload["assembled_mvp_claimed"] is False
    assert payload["path"] == "browser-to-credit-fixture"
    assert payload["sn009_authority_exercised"] is True
    assert payload["contract_sha256"] == CONTRACT_SHA256


def test_cli_real_peers_without_evidence_fails(capsys) -> None:
    code = main(["run", "--mode", "real-peers", "--run-id", "cli-strict"])
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
