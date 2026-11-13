from __future__ import annotations

import json
from pathlib import Path

from sentinel_dispatcher.domain.digest import action_digest, canonical_action

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "demo_command.json"


def test_canonical_digest_matches_baseline_fixture() -> None:
    fixture = json.loads(FIXTURES.read_text(encoding="utf-8"))
    payload = fixture["claim_one_response"]["commands"][0]["payload"]
    assert canonical_action(payload) == fixture["canonical_action_utf8"].encode("utf-8")
    assert action_digest(payload) == fixture["expected_sha256"]
