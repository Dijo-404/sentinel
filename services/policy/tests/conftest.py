"""Shared fixtures: fixed clock, principals, base refund request."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sentinel_policy.adapters.auth import TokenMap
from sentinel_policy.adapters.catalog import PolicyCatalog
from sentinel_policy.adapters.clock import FixedClock
from sentinel_policy.adapters.http import create_app
from sentinel_policy.application.evaluate import EvaluatePolicy
from sentinel_policy.application.list_policies import ListPolicies
from sentinel_policy.contracts import parse_policy_request

MODULE_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = MODULE_ROOT / "contracts"
NOW = datetime(2026, 11, 13, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def clock(now: datetime) -> FixedClock:
    return FixedClock(now)


@pytest.fixture
def tokens() -> TokenMap:
    return TokenMap.from_path(CONTRACTS / "principals.json")


@pytest.fixture
def evaluate(clock: FixedClock) -> EvaluatePolicy:
    return EvaluatePolicy(clock)


@pytest.fixture
def catalog() -> PolicyCatalog:
    return PolicyCatalog.from_path(CONTRACTS / "policies.json")


@pytest.fixture
def list_policies(catalog: PolicyCatalog) -> ListPolicies:
    return ListPolicies(catalog)


@pytest.fixture
def client(evaluate: EvaluatePolicy, tokens: TokenMap, list_policies: ListPolicies) -> TestClient:
    app = create_app(
        evaluate=evaluate,
        tokens=tokens,
        list_policies=list_policies,
        mode="fixture",
    )
    return TestClient(app)


@pytest.fixture
def allow_request() -> dict:
    raw = json.loads((CONTRACTS / "policy.v1.allow.request.json").read_text(encoding="utf-8"))
    return copy.deepcopy(raw)


@pytest.fixture
def allow_policy_request(allow_request: dict):
    return parse_policy_request(allow_request)


@pytest.fixture
def workflow_auth() -> dict[str, str]:
    return {"Authorization": "Bearer workflow-demo-token"}


@pytest.fixture
def platform_admin_auth() -> dict[str, str]:
    return {"Authorization": "Bearer tok-platform-admin"}


@pytest.fixture
def sandbox_admin_auth() -> dict[str, str]:
    return {"Authorization": "Bearer tok-sandbox-admin"}
