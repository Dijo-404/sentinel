"""Shared fixtures for merchant-settlement checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sentinel_merchant_settlement.adapters.evidence_stub import StubEvidence
from sentinel_merchant_settlement.adapters.provider_stub import StubPaymentProvider
from sentinel_merchant_settlement.adapters.store_memory import MemoryFindingStore
from sentinel_merchant_settlement.bootstrap import Settings, build_app
from sentinel_merchant_settlement.domain.reconcile import canonical_batch_digest
from sentinel_merchant_settlement.domain.types import SettlementRow

MODULE_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = MODULE_ROOT / "fixtures"
CONTRACTS = MODULE_ROOT / "contracts"


@pytest.fixture
def principals_path() -> Path:
    return CONTRACTS / "principals.json"


@pytest.fixture
def fixture_batch_dict() -> dict:
    raw = json.loads((FIXTURES / "settlement_batch.json").read_text(encoding="utf-8"))
    rows = [
        SettlementRow(
            row_id=item["row_id"],
            transaction_ref=item["transaction_ref"],
            order_ref=item.get("order_ref"),
            settled_minor=item["settled_minor"],
            fee_minor=item["fee_minor"],
            occurred_at=item["occurred_at"],
        )
        for item in raw["rows"]
    ]
    raw["source_digest"] = canonical_batch_digest(rows)
    return raw


@pytest.fixture
def app(principals_path: Path):
    settings = Settings(
        mode="fixture",
        principals_path=principals_path,
        contract_version="sentinel.task-contracts.v1",
        evidence_base_url="",
        evidence_token="",
        provider_base_url="",
        provider_token="",
    )
    return build_app(
        settings,
        evidence=StubEvidence(),
        provider=StubPaymentProvider(),
        store=MemoryFindingStore(),
    )


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_header() -> dict[str, str]:
    return {"Authorization": "Bearer operator-demo-token"}
