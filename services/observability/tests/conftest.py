"""Shared fixtures: synthetic admin principals and in-memory signal store."""

from __future__ import annotations

import pytest

from sentinel_observability.adapters.auth import TokenAuthenticator
from sentinel_observability.adapters.http_api import AppServices, create_app
from sentinel_observability.adapters.memory_store import MemorySignalStore
from sentinel_observability.application.service import ObservabilityService
from sentinel_observability.domain.types import Principal, Signal

ADMIN = Principal(
    principal_id="admin-1",
    tenant_id="tenant-demo",
    roles=("platform_admin",),
)

TOKENS = {
    "admin-token": ADMIN,
    "sandbox-admin-token": Principal(
        principal_id="admin-sandbox",
        tenant_id="tenant-demo",
        roles=("sandbox-admin",),
    ),
    "other-tenant-token": Principal(
        principal_id="admin-2",
        tenant_id="tenant-other",
        roles=("platform_admin",),
    ),
    "operator-token": Principal(
        principal_id="op-1",
        tenant_id="tenant-demo",
        roles=("operator",),
    ),
}


@pytest.fixture
def store():
    return MemorySignalStore()


@pytest.fixture
def service(store):
    return ObservabilityService(store=store)


@pytest.fixture
def app(service):
    return create_app(
        AppServices(
            authenticator=TokenAuthenticator(TOKENS),
            service=service,
            mode="fixture",
        )
    )


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def auth(token: str = "admin-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def sample_signal(**overrides) -> Signal:
    base = {
        "signal_id": "sig-1",
        "tenant_id": "tenant-demo",
        "kind": "span",
        "name": "request.handle",
        "attributes": {"request_id": "req-demo-1", "case_id": "case-demo-42"},
        "events": [{"name": "accepted", "attributes": {"event.kind": "accepted"}}],
        "recorded_at": "2026-11-14T12:00:00Z",
    }
    base.update(overrides)
    return Signal(**base)
