from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sentinel_simulator.composition.app import create_app


@pytest.fixture()
def client() -> TestClient:
    app = create_app(mode="fixture")
    with TestClient(app) as test_client:
        yield test_client
