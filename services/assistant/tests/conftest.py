"""Shared fixtures: synthetic principals, fixed clock, memory store."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sentinel_assistant.adapters.auth import TokenAuthenticator
from sentinel_assistant.adapters.clock import FixedClock
from sentinel_assistant.adapters.http_api import AppServices, create_app
from sentinel_assistant.adapters.storage_memory import MemoryAssistantStore
from sentinel_assistant.application.service import AssistantService
from sentinel_assistant.domain.types import Principal

CUSTOMER = Principal(
    principal_id="customer-demo",
    tenant_id="tenant-demo",
    roles=("customer",),
)
OPERATOR = Principal(
    principal_id="operator-demo",
    tenant_id="tenant-demo",
    roles=("operator",),
)
OTHER_TENANT = Principal(
    principal_id="customer-other",
    tenant_id="tenant-other",
    roles=("customer",),
)

TOKENS = {
    "tok-customer": CUSTOMER,
    "operator-token": OPERATOR,
    "tok-other": OTHER_TENANT,
}


@pytest.fixture
def clock():
    return FixedClock(datetime(2026, 11, 15, 10, 0, tzinfo=UTC))


@pytest.fixture
def store():
    return MemoryAssistantStore()


@pytest.fixture
def service(store, clock):
    from sentinel_assistant.adapters.sandbox_reply import SandboxEchoReply

    return AssistantService(store=store, clock=clock, replies=SandboxEchoReply())


@pytest.fixture
def app(service):
    return create_app(
        AppServices(
            authenticator=TokenAuthenticator(TOKENS),
            assistant=service,
            mode="fixture",
        )
    )


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def auth(token: str = "tok-customer") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
