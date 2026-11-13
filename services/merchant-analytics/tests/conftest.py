"""Shared pytest fixtures for merchant-analytics."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from constants import EXPECTED, TOKENS
from sentinel_merchant_analytics.bootstrap import Settings, build_app


@pytest.fixture
def expected_metrics() -> dict:
    return dict(EXPECTED)


@pytest.fixture
def fixture_settings() -> Settings:
    return Settings(
        mode="fixture",
        tokens=TOKENS,
        case_api_base_url="",
        case_api_token="",
        evidence_base_url="",
        evidence_token="",
        contract_version="sentinel.task-contracts.v1",
    )


@pytest.fixture
def client(fixture_settings: Settings) -> TestClient:
    app = build_app(fixture_settings)
    return TestClient(app)


@pytest.fixture
def metrics_url() -> str:
    return f"/v1/merchants/{EXPECTED['merchant_ref']}/metrics"
