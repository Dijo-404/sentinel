"""Shared fixtures: synthetic principals and in-memory activity store."""

from __future__ import annotations

import pytest

from sentinel_ops_activity.adapters.auth import TokenAuthenticator
from sentinel_ops_activity.adapters.http_api import AppServices, create_app
from sentinel_ops_activity.adapters.memory_store import MemoryActivityStore
from sentinel_ops_activity.application.activity import ActivityService
from sentinel_ops_activity.domain.types import ActivityItem, Principal

OPERATOR = Principal(
    principal_id="op-1",
    tenant_id="tenant-demo",
    roles=("operator",),
)

TOKENS = {
    "operator-token": OPERATOR,
    "supervisor-token": Principal(
        principal_id="sup-1",
        tenant_id="tenant-demo",
        roles=("supervisor",),
    ),
    "other-tenant-token": Principal(
        principal_id="op-2",
        tenant_id="tenant-other",
        roles=("operator",),
    ),
    "customer-token": Principal(
        principal_id="cust-1",
        tenant_id="tenant-demo",
        roles=("customer",),
    ),
}


@pytest.fixture
def store():
    return MemoryActivityStore()


@pytest.fixture
def service(store):
    return ActivityService(store=store)


@pytest.fixture
def app(service):
    return create_app(
        AppServices(
            authenticator=TokenAuthenticator(TOKENS),
            activity=service,
            mode="fixture",
        )
    )


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def auth(token: str = "operator-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def sample_item(**overrides) -> ActivityItem:
    base = {
        "activity_id": "act-1",
        "tenant_id": "tenant-demo",
        "kind": "case.opened",
        "summary": "Case case-demo-42 opened",
        "occurred_at": "2026-11-14T12:00:00Z",
        "case_id": "case-demo-42",
    }
    base.update(overrides)
    return ActivityItem(**base)
