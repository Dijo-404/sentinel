"""Capabilities and contract snapshot smoke."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "identity.v1.json"


def test_capabilities(client: TestClient) -> None:
    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["component"] == "identity"
    assert body["mode"] == "fixture"
    assert body["money_authority"] is False
    assert body["contract_version"] == "sentinel.task-contracts.v1"


def test_contract_snapshot_exists() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["port"] == "identity.v1"
    assert payload["contract_sha256"].startswith("0db3ba2")
