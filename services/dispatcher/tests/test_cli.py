from __future__ import annotations

import json

from sentinel_dispatcher.cli import main
from sentinel_dispatcher.composition import CONTRACT_HASH, capabilities


def test_capabilities_cli(capsys) -> None:
    assert main(["capabilities", "--mode", "fixture"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == capabilities(mode="fixture")
    assert payload["contract_sha256"] == CONTRACT_HASH
    assert payload["port"] == "dispatcher.v1"


def test_migrate_requires_database_url(capsys) -> None:
    assert main(["migrate"]) == 2
    assert "DATABASE_URL" in capsys.readouterr().err
