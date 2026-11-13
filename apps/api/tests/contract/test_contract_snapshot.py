"""Pinned contract baseline hash and route inventory."""

import hashlib
import json
from pathlib import Path

from sentinel_api import CONTRACT_HASH, CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[4]
CONTRACT_DOC = ROOT / "docs" / "independent-task-contracts.md"
SNAPSHOT = Path(__file__).resolve().parents[2] / "contracts" / "case-api.v1.snapshot.json"


def test_contract_hash_matches_pinned_baseline():
    digest = hashlib.sha256(CONTRACT_DOC.read_bytes()).hexdigest()
    assert digest == CONTRACT_HASH
    assert CONTRACT_VERSION == "sentinel.task-contracts.v1"


def test_snapshot_lists_case_api_routes():
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert data["sha256"] == CONTRACT_HASH
    assert "POST /v1/cases" in data["routes"]
    assert "POST /v1/internal/cases/{case_id}/results" in data["routes"]
