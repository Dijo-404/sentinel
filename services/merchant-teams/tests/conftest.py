"""Shared fixtures: synthetic principals, fixed clock, in-memory store."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from sentinel_merchant_teams.adapters.auth import TokenAuthenticator
from sentinel_merchant_teams.adapters.case_api_stub import StubCaseApi
from sentinel_merchant_teams.adapters.clock import FixedClock
from sentinel_merchant_teams.adapters.http_api import AppServices, create_app
from sentinel_merchant_teams.adapters.storage_memory import MemoryStaffStore
from sentinel_merchant_teams.application.staff import StaffService
from sentinel_merchant_teams.domain.types import Principal

OPERATOR = Principal(
    principal_id="op-1",
    tenant_id="tenant-demo",
    roles=("operator",),
    subject_refs=("merchant-demo-1",),
    case_ids=("case-demo-42",),
)

SUPERVISOR = Principal(
    principal_id="sup-1",
    tenant_id="tenant-demo",
    roles=("supervisor",),
    subject_refs=("merchant-demo-1", "*"),
    case_ids=("case-demo-42",),
)

OUTSIDER = Principal(
    principal_id="op-other",
    tenant_id="tenant-other",
    roles=("operator",),
    subject_refs=("merchant-other",),
    case_ids=("case-other",),
)

TOKENS = {
    "operator-token": OPERATOR,
    "supervisor-token": SUPERVISOR,
    "outsider-token": OUTSIDER,
}


@pytest.fixture
def clock():
    return FixedClock(datetime(2026, 11, 13, 12, 0, tzinfo=UTC))


@pytest.fixture
def store():
    return MemoryStaffStore()


@pytest.fixture
def cases():
    return StubCaseApi(mode="valid")


@pytest.fixture
def service(store, cases, clock):
    return StaffService(store, cases, clock)


@pytest.fixture
def app(store, cases, clock):
    services = AppServices(
        authenticator=TokenAuthenticator(TOKENS),
        staff=StaffService(store, cases, clock),
        mode="fixture",
    )
    return create_app(services)


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer operator-token"}
