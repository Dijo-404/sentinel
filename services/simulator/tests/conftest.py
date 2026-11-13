from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sentinel_simulator.composition.app import create_app


@pytest.fixture()
def client() -> TestClient:
    app = create_app(mode="fixture", sandbox=True)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def real_peers_client() -> TestClient:
    app = create_app(mode="real-peers", sandbox=True)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def non_sandbox_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SIMULATOR_TENANT_ID", "tenant-other")
    app = create_app(mode="fixture", sandbox=False)
    with TestClient(app) as test_client:
        yield test_client
