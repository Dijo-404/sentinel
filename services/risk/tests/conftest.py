"""Shared fixtures: synthetic principals, fixed clock, fixture peers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sentinel_risk.adapters.auth import TokenAuthenticator
from sentinel_risk.adapters.clock import FixedClock
from sentinel_risk.adapters.http_api import AppServices, create_app
from sentinel_risk.adapters.peers_fixture import FixtureCaseApi, FixtureWorkflow
from sentinel_risk.adapters.storage_memory import MemoryRiskStore
from sentinel_risk.application.risk import RiskService
from sentinel_risk.domain.types import Principal

RISK_OFFICER = Principal(
    principal_id="risk-1",
    tenant_id="tenant-demo",
    roles=("risk_officer",),
    subject_refs=("subj-demo-1",),
    case_ids=("case-demo-42", "case-fraud-99"),
    queue_refs=("FRAUD",),
)

TOKENS = {
    "risk-token": RISK_OFFICER,
    "risk-other-tenant": Principal(
        "risk-2",
        "tenant-other",
        ("risk_officer",),
        ("subj-other",),
        ("case-demo-42",),
        ("FRAUD",),
    ),
    "operator-token": Principal(
        "op-1",
        "tenant-demo",
        ("operator",),
        ("subj-demo-1",),
        ("case-demo-42",),
        ("FRAUD",),
    ),
    "supervisor-token": Principal(
        "sup-1",
        "tenant-demo",
        ("supervisor",),
        ("subj-demo-1",),
        ("case-demo-42",),
        ("FRAUD",),
    ),
}


@pytest.fixture
def clock():
    return FixedClock(datetime(2026, 11, 14, 10, 0, tzinfo=UTC))


@pytest.fixture
def store():
    return MemoryRiskStore()


@pytest.fixture
def case_api():
    return FixtureCaseApi()


@pytest.fixture
def workflow():
    return FixtureWorkflow()


@pytest.fixture
def service(case_api, workflow, store, clock):
    return RiskService(
        case_api=case_api,
        workflow=workflow,
        store=store,
        clock=clock,
    )


@pytest.fixture
def app(service):
    return create_app(
        AppServices(
            authenticator=TokenAuthenticator(TOKENS),
            risk=service,
            mode="fixture",
        )
    )


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def auth(token: str = "risk-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
