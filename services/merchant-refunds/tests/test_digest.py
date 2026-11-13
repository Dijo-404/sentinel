"""Canonical digest matches pinned baseline fixture."""

from __future__ import annotations

import json
from pathlib import Path

from sentinel_merchant_refunds.domain.digest import action_digest, canonical_action_bytes

FIXTURE = Path(__file__).resolve().parents[1] / "contracts" / "digest-fixture.json"


def test_canonical_digest_matches_baseline():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload = data["payload"]
    assert canonical_action_bytes(payload).decode("utf-8") == data["canonical_action_utf8"]
    assert action_digest(payload) == data["expected_sha256"]
