"""CLI capabilities output."""

from __future__ import annotations

import json

from sentinel_verifier.cli import main


def test_capabilities(capsys):
    assert main(["capabilities", "--mode", "fixture"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["component"] == "verifier"
    assert payload["port"] == "verifier.v1"
    assert payload["contract_sha256"].startswith("0db3ba2b")
