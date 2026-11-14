"""Sandbox seed: ops escalations / messages / history / audit for tenant-demo."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from sentinel_api.adapters.db.repository import SqlCaseRepository
from sentinel_api.adapters.http.app import create_app
from sentinel_api.adapters.http.auth import CompositePrincipalResolver, TokenMap
from sentinel_api.adapters.identity.fixture import FixtureIdentityPrincipalAdapter
from sentinel_api.adapters.peers.fixture_clients import (
    FixtureEvidenceClient,
    FixtureLedgerClient,
    FixtureVerifierClient,
    FixtureWorkflowClient,
)
from sentinel_api.adapters.seed import (
    SEED_ESCALATED_CASE_ID,
    SEED_HISTORY_CASE_ID,
    SEED_TENANT_ID,
    seed_ops_surfaces,
)
from sentinel_api.application.service import CaseService
from sentinel_api.bootstrap import SecureIds, SystemClock
from tests.conftest import IDENTITY_PATH, TOKENS_PATH, auth


def test_seed_refuses_non_demo_tenant() -> None:
    report = seed_ops_surfaces(
        {
            "CORE_ASSEMBLY_TENANT_ID": "tenant-prod",
            "SENTINEL_V1_SANDBOX": "1",
            "SENTINEL_API_DATABASE_URL": "postgresql+psycopg://x/y",
        }
    )
    assert report["status"] == "FAIL"
    assert report["reason_code"] == "SANDBOX_TENANT_REQUIRED"
    assert report["rows"] == 0


def test_seed_refuses_when_sandbox_flag_missing() -> None:
    report = seed_ops_surfaces(
        {
            "CORE_ASSEMBLY_TENANT_ID": "tenant-demo",
            "SENTINEL_V1_SANDBOX": "0",
            "SENTINEL_API_DATABASE_URL": "postgresql+psycopg://x/y",
        }
    )
    assert report["status"] == "FAIL"
    assert report["reason_code"] == "SANDBOX_FLAG_REQUIRED"
    assert report["rows"] == 0


def test_seed_refuses_non_postgres_url() -> None:
    report = seed_ops_surfaces(
        {
            "CORE_ASSEMBLY_TENANT_ID": "tenant-demo",
            "SENTINEL_V1_SANDBOX": "1",
            "SENTINEL_API_DATABASE_URL": "sqlite:///tmp.db",
        }
    )
    assert report["status"] == "FAIL"
    assert report["reason_code"] == "POSTGRES_URL_REQUIRED"
    assert report["rows"] == 0


def test_seed_ops_surfaces_present(engine, monkeypatch: pytest.MonkeyPatch) -> None:
    url = engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("SENTINEL_API_DATABASE_URL", url)
    monkeypatch.setenv("SENTINEL_V1_SANDBOX", "1")
    monkeypatch.setenv("CORE_ASSEMBLY_TENANT_ID", "tenant-demo")

    report = seed_ops_surfaces(os.environ)
    assert report["status"] == "PASS"
    assert report["tenant_id"] == SEED_TENANT_ID
    assert report["rows"] >= 2
    assert SEED_ESCALATED_CASE_ID in report["case_ids"]
    assert SEED_HISTORY_CASE_ID in report["case_ids"]

    # Idempotent re-seed.
    again = seed_ops_surfaces(os.environ)
    assert again["status"] == "PASS"
    assert again["case_ids"] == report["case_ids"]

    repo = SqlCaseRepository(engine)
    peers = {
        "workflow": FixtureWorkflowClient(),
        "evidence": FixtureEvidenceClient(),
        "ledger": FixtureLedgerClient(),
        "verifier": FixtureVerifierClient(),
    }
    service = CaseService(
        repo=repo,
        clock=SystemClock(),
        ids=SecureIds(),
        workflow=peers["workflow"],
        evidence=peers["evidence"],
        ledger=peers["ledger"],
        verifier=peers["verifier"],
        service_authorization="Bearer token-case-api-service",
    )
    tokens = TokenMap.from_path(TOKENS_PATH)
    identity = FixtureIdentityPrincipalAdapter.from_path(IDENTITY_PATH)
    resolver = CompositePrincipalResolver(identity=identity, tokens=tokens)

    def readiness():
        repo.ping()
        return {"ready": True, "mode": "fixture", "label": "fixture-local"}

    application = create_app(service=service, tokens=resolver, mode="fixture", readiness=readiness)
    with TestClient(application) as client:
        escalated = client.get("/v1/ops/cases?status=ESCALATED", headers=auth("token-operator"))
        assert escalated.status_code == 200
        esc_ids = {c["case_id"] for c in escalated.json()["cases"]}
        assert SEED_ESCALATED_CASE_ID in esc_ids

        history = client.get("/v1/ops/cases?status=HISTORY", headers=auth("token-supervisor"))
        assert history.status_code == 200
        hist = {c["case_id"]: c["status"] for c in history.json()["cases"]}
        assert hist.get(SEED_HISTORY_CASE_ID) in {"VERIFIED_RESOLVED", "CLOSED_NO_ACTION"}

        messages = client.get("/v1/ops/messages", headers=auth("token-operator"))
        assert messages.status_code == 200
        msg_cases = {m["case_id"] for m in messages.json()["messages"]}
        assert SEED_ESCALATED_CASE_ID in msg_cases or SEED_HISTORY_CASE_ID in msg_cases

        audit = client.get("/v1/ops/audit-events", headers=auth("token-supervisor"))
        assert audit.status_code == 200
        event_cases = {e["case_id"] for e in audit.json()["events"]}
        assert SEED_ESCALATED_CASE_ID in event_cases or SEED_HISTORY_CASE_ID in event_cases
