"""Shared pytest fixtures for identity.v1."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sentinel_identity.adapters.clock import SystemClock
from sentinel_identity.adapters.seed import DEMO_PASSWORD, load_seed_users
from sentinel_identity.adapters.storage_memory import MemoryIdentityStore
from sentinel_identity.bootstrap import Settings, build_app

# Seed login may keep a short fixture hash; new register/accept must meet the floor.
NEW_PASSWORD = "fixture-pass-1"


@pytest.fixture
def demo_password() -> str:
    return DEMO_PASSWORD


@pytest.fixture
def new_password() -> str:
    return NEW_PASSWORD


@pytest.fixture
def store() -> MemoryIdentityStore:
    memory = MemoryIdentityStore()
    load_seed_users(memory, SystemClock())
    return memory


@pytest.fixture
def client(store: MemoryIdentityStore) -> TestClient:
    app = build_app(
        Settings(
            mode="fixture",
            contract_version="sentinel.task-contracts.v1",
            database_url="",
            seed=False,
            accept_link_base="http://127.0.0.1:3000",
            expose_sandbox_codes=False,
            sandbox=True,
            sandbox_token="test-sandbox-token",
        ),
        store=store,
    )
    return TestClient(app)


def login(
    client: TestClient,
    email: str,
    password: str,
    *,
    requested_role: str | None = None,
) -> dict:
    body: dict = {"email": email, "password": password}
    if requested_role is not None:
        body["requested_role"] = requested_role
    response = client.post("/v1/auth/login", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
