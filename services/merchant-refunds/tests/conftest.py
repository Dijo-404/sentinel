"""Shared fixtures for merchant-refunds tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from tests.stubs import StubCaseApi, StubEvidence, StubLedger, StubPolicy

from sentinel_merchant_refunds.adapters.auth import TokenPrincipalMap, demo_principals
from sentinel_merchant_refunds.adapters.clock import FixedClock
from sentinel_merchant_refunds.adapters.ids import SecureIdGenerator
from sentinel_merchant_refunds.adapters.memory_store import MemoryRequestStore
from sentinel_merchant_refunds.application.service import MerchantRefundService
from sentinel_merchant_refunds.bootstrap import build_app
from sentinel_merchant_refunds.domain.types import DraftCreate, Principal


@pytest.fixture
def principal() -> Principal:
    return Principal(
        principal_id="staff-demo-1",
        tenant_id="tenant-demo-1",
        merchant_ref="merchant-demo-1",
        roles=["merchant_staff"],
    )


@pytest.fixture
def peers():
    case_api = StubCaseApi()
    evidence = StubEvidence()
    evidence.seed_demo()
    policy = StubPolicy()
    ledger = StubLedger()
    return case_api, evidence, policy, ledger


@pytest.fixture
def service(peers) -> MerchantRefundService:
    case_api, evidence, policy, ledger = peers
    return MerchantRefundService(
        store=MemoryRequestStore(),
        case_api=case_api,
        evidence=evidence,
        policy=policy,
        ledger=ledger,
        clock=FixedClock("2026-11-13T12:00:00Z"),
        ids=SecureIdGenerator(),
    )


@pytest.fixture
def client(peers):
    case_api, evidence, policy, ledger = peers
    app = build_app(
        store=MemoryRequestStore(),
        case_api=case_api,
        evidence=evidence,
        policy=policy,
        ledger=ledger,
        auth=TokenPrincipalMap(demo_principals()),
        clock=FixedClock("2026-11-13T12:00:00Z"),
        mode="fixture",
    )
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer token-merchant-refunds-demo",
        "Idempotency-Key": "idem-demo-1",
    }


@pytest.fixture
def draft_body() -> dict:
    return DraftCreate(
        case_id="case-demo-42",
        transaction_ref="TXN-B",
        amount_minor=150000,
        currency="INR",
        evidence_ids=["evidence-payment-b", "evidence-order"],
        rationale="Duplicate capture on DEMO-ORDER-42",
    ).model_dump()
