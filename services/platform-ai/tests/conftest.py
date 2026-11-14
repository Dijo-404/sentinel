"""Shared pytest fixtures for platform-ai.v1."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sentinel_platform_ai.adapters.storage_memory import MemoryPlatformAiStore
from sentinel_platform_ai.bootstrap import Settings, build_app
from sentinel_platform_ai.domain.types import AiConfig, AiModel, AiRun
from sentinel_platform_ai.seed import (
    SEED_CONFIG_UPDATED_AT,
    SEED_MODEL_ID,
    SEED_RUN_ID,
    SEED_RUN_STARTED_AT,
    SEED_TENANT_ID,
)

TOKENS = (
    "admin-token=admin-1|tenant-demo|platform_admin||;"
    "operator-token=op-1|tenant-demo|operator||;"
    "other-tenant-token=admin-2|tenant-other|platform_admin||"
)

MONEY_KEYS = frozenset(
    {
        "amount",
        "amount_minor",
        "currency",
        "refund",
        "refund_id",
        "payment",
        "payment_id",
        "ledger",
        "reservation",
        "money",
    }
)


@pytest.fixture
def seeded_store() -> MemoryPlatformAiStore:
    store = MemoryPlatformAiStore()
    store.put_config(
        AiConfig(
            tenant_id=SEED_TENANT_ID,
            models=(
                AiModel(
                    model_id=SEED_MODEL_ID,
                    label="Sandbox chat",
                    provider="sandbox",
                ),
            ),
            kill_switch=False,
            updated_at=SEED_CONFIG_UPDATED_AT,
        )
    )
    store.put_run(
        AiRun(
            run_id=SEED_RUN_ID,
            tenant_id=SEED_TENANT_ID,
            model_id=SEED_MODEL_ID,
            status="SUCCEEDED",
            started_at=SEED_RUN_STARTED_AT,
        )
    )
    return store


@pytest.fixture
def client(seeded_store: MemoryPlatformAiStore) -> TestClient:
    app = build_app(
        Settings(
            mode="fixture",
            tokens=TOKENS,
            contract_version="sentinel.task-contracts.v1",
            database_url="",
        ),
        store=seeded_store,
    )
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer admin-token"}
