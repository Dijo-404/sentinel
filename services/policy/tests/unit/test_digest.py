"""Canonical digest must match the pinned contract fixture."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_policy.contracts import action_digest, canonical_action_bytes

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"


def test_canonical_digest_matches_baseline_fixture() -> None:
    fixture = json.loads((CONTRACTS / "digest-fixture.json").read_text(encoding="utf-8"))
    payload = json.loads(fixture["canonical_action_utf8"])
    assert canonical_action_bytes(payload).decode("utf-8") == fixture["canonical_action_utf8"]
    assert action_digest(payload) == fixture["expected_sha256"]
