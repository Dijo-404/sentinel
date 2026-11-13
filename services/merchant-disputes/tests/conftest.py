"""Shared fixtures: synthetic principals, fixed clock, fixture peers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sentinel_merchant_disputes.adapters.auth import TokenAuthenticator
from sentinel_merchant_disputes.adapters.clock import FixedClock
from sentinel_merchant_disputes.adapters.http_api import AppServices, create_app
from sentinel_merchant_disputes.adapters.peers_fixture import FixtureCaseApi, FixtureEvidence
from sentinel_merchant_disputes.adapters.storage_memory import MemoryDisputeStore
from sentinel_merchant_disputes.application.disputes import DisputeService
from sentinel_merchant_disputes.domain.types import Principal

OPERATOR = Principal(
    principal_id="op-1",
    tenant_id="tenant-demo",
    roles=("operator",),
    subject_refs=("subj-demo-1",),
    case_ids=("case-demo-42",),
    merchant_refs=("merchant-demo",),
)

TOKENS = {
    "operator-token": OPERATOR,
    "supervisor-token": Principal(
        "sup-1",
        "tenant-demo",
        ("supervisor",),
        ("subj-demo-1",),
        ("case-demo-42",),
        ("merchant-demo",),
    ),
    "other-merchant-token": Principal(
        "op-2",
        "tenant-demo",
        ("operator",),
        ("subj-demo-1",),
        ("case-demo-42",),
        ("other-merchant",),
    ),
    "customer-token": Principal(
        "cust-1",
        "tenant-demo",
        ("customer",),
        ("subj-demo-1",),
        ("case-demo-42",),
        ("merchant-demo",),
    ),
}


@pytest.fixture
def clock():
    return FixedClock(datetime(2026, 11, 13, 12, 30, tzinfo=UTC))


@pytest.fixture
def store():
    return MemoryDisputeStore()


@pytest.fixture
def case_api():
    return FixtureCaseApi()


@pytest.fixture
def evidence():
    return FixtureEvidence()


@pytest.fixture
def service(case_api, evidence, store, clock):
    return DisputeService(
        case_api=case_api,
        evidence=evidence,
        store=store,
        clock=clock,
        default_deadline_seconds=3600,
    )


@pytest.fixture
def app(service):
    return create_app(
        AppServices(
            authenticator=TokenAuthenticator(TOKENS),
            disputes=service,
            mode="fixture",
        )
    )


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def auth(token: str = "operator-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
