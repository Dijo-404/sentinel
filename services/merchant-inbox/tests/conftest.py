"""Shared fixtures for merchant-inbox checks."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.stubs.case_api import StubCaseApi
from tests.stubs.evidence import StubEvidence

from sentinel_merchant_inbox.adapters.local_peers import default_valid_peers
from sentinel_merchant_inbox.bootstrap import build_app


@pytest.fixture
def peers():
    return default_valid_peers()


@pytest.fixture
def app(peers):
    case_api, evidence = peers
    return build_app(case_api=case_api, evidence=evidence, mode="fixture")


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def merchant_auth() -> dict[str, str]:
    return {"Authorization": "Bearer merchant-op-demo-token"}


@pytest.fixture
def supervisor_auth() -> dict[str, str]:
    return {"Authorization": "Bearer merchant-supervisor-demo-token"}


@pytest.fixture
def other_tenant_auth() -> dict[str, str]:
    return {"Authorization": "Bearer merchant-other-tenant-token"}


@pytest.fixture
def customer_auth() -> dict[str, str]:
    return {"Authorization": "Bearer customer-demo-token"}


@pytest.fixture
def unavailable_peers():
    return StubCaseApi(mode="unavailable"), StubEvidence(mode="unavailable")
