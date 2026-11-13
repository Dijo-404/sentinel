from __future__ import annotations

import json
from pathlib import Path

from sentinel_replay.application.service import compare_candidates
from sentinel_replay.fixtures import CONTRACT_HASH, CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def test_contract_baseline_hash_pinned() -> None:
    assert CONTRACT_HASH == ("0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa")
    assert CONTRACT_VERSION == "sentinel.task-contracts.v1"


def test_run_report_matches_tool_port_shape() -> None:
    report = compare_candidates(run_id="shape-1").to_dict()
    assert report["contract_version"] == CONTRACT_VERSION
    assert report["mode"] == "fixture"
    assert report["status"] in {"PASS", "FAIL", "UNVERIFIED"}
    assert isinstance(report["checks"], list)
    assert {"name", "status", "reason_code"} <= set(report["checks"][0])
    art = report["output_artifacts"][0]
    assert {"kind", "uri", "sha256", "component_version", "evidence_mode"} <= set(art)


def test_example_snapshot_present() -> None:
    example = json.loads((CONTRACTS / "replay.v1.example.json").read_text(encoding="utf-8"))
    assert example["contract_version"] == CONTRACT_VERSION
    assert example["modes"]["seed"] == 42
