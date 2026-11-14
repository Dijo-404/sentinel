"""Shared pytest fixtures for evaluation.v1 HTTP report serve."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sentinel_evaluation.adapters.storage_memory import MemoryReportStore
from sentinel_evaluation.composition.http_app import Settings, build_app
from sentinel_evaluation.domain.models import CONTRACT_VERSION
from sentinel_evaluation.seed import seed_report_wire

TOKENS = (
    "admin-token=admin-1|tenant-demo|platform_admin||;operator-token=op-1|tenant-demo|operator||"
)


@pytest.fixture
def seeded_store() -> MemoryReportStore:
    store = MemoryReportStore()
    store.put_report(seed_report_wire())
    return store


@pytest.fixture
def client(seeded_store: MemoryReportStore) -> TestClient:
    app = build_app(
        Settings(
            mode="fixture",
            tokens=TOKENS,
            contract_version=CONTRACT_VERSION,
            database_url="",
        ),
        store=seeded_store,
    )
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer admin-token"}
