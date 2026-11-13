"""Shared fixtures for merchant-sla tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sentinel_merchant_sla.adapters.case_api_fixture import FixtureCaseApi
from sentinel_merchant_sla.adapters.clock import FixedClock
from sentinel_merchant_sla.adapters.memory_store import MemorySlaStore
from sentinel_merchant_sla.application.service import MerchantSlaService
from sentinel_merchant_sla.bootstrap import Settings, build_app

MODULE_ROOT = Path(__file__).resolve().parents[1]
PRINCIPALS = MODULE_ROOT / "contracts" / "principals.json"
T0 = datetime(2026, 11, 13, 10, 0, 0, tzinfo=UTC)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(T0)


@pytest.fixture
def store() -> MemorySlaStore:
    return MemorySlaStore()


@pytest.fixture
def case_api() -> FixtureCaseApi:
    return FixtureCaseApi(behavior="valid")


@pytest.fixture
def service(
    store: MemorySlaStore, clock: FixedClock, case_api: FixtureCaseApi
) -> MerchantSlaService:
    return MerchantSlaService(store=store, clock=clock, case_api=case_api)


@pytest.fixture
def client(store: MemorySlaStore, clock: FixedClock, case_api: FixtureCaseApi) -> TestClient:
    app = build_app(
        settings=Settings(
            mode="fixture",
            principals_path=PRINCIPALS,
            case_api_base_url="",
            case_api_token="",
        ),
        clock=clock,
        store=store,
        case_api=case_api,
    )
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer merchant-ops-demo-token"}
