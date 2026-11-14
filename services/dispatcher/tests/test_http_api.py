from __future__ import annotations

from fastapi.testclient import TestClient

from sentinel_dispatcher.composition import CONTRACT_HASH, CONTRACT_VERSION, build_http_app


def test_probe_routes_fixture_mode() -> None:
    client = TestClient(build_http_app(mode="fixture"))
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready", "mode": "fixture"}
    caps = client.get("/v1/capabilities").json()
    assert caps == {
        "contract_version": CONTRACT_VERSION,
        "component": "dispatcher",
        "mode": "fixture",
        "port": "dispatcher.v1",
        "contract_sha256": CONTRACT_HASH,
    }


def test_probe_routes_real_peers_mode() -> None:
    client = TestClient(build_http_app(mode="real-peers"))
    assert client.get("/readyz").json()["mode"] == "real-peers"
    assert client.get("/v1/capabilities").json()["mode"] == "real-peers"
