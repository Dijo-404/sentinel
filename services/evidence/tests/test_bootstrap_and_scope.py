"""Postgres required by default; empty case scope denies; '*' allows all."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sentinel_evidence.adapters.auth import TokenAuthenticator
from sentinel_evidence.adapters.http_api import AppServices, create_app
from sentinel_evidence.adapters.provider_stub import CaseSelectingStub
from sentinel_evidence.adapters.storage_memory import MemoryEvidenceStore
from sentinel_evidence.application.collect import CollectEvidence, ListEvidence
from sentinel_evidence.application.errors import ConfigurationError
from sentinel_evidence.bootstrap import Settings, build_app
from sentinel_evidence.domain.types import CONTRACT_VERSION, Principal


def test_real_peers_without_database_url_hard_fails():
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        build_app(
            Settings(
                mode="real-peers",
                database_url=None,
                schema="evidence",
                tokens="t=p|tenant|workflow|s|c",
                provider_base_url="http://provider.test",
                provider_token="tok",
                ttl_seconds=60,
                contract_version=CONTRACT_VERSION,
                allow_memory=False,
            )
        )


def test_allow_memory_flag_permits_memory_store():
    app = build_app(
        Settings(
            mode="real-peers",
            database_url=None,
            schema="evidence",
            tokens="t=p|tenant|workflow|subj-demo-1|case-demo-42",
            provider_base_url="http://provider.test",
            provider_token="tok",
            ttl_seconds=60,
            contract_version=CONTRACT_VERSION,
            allow_memory=True,
        ),
        use_memory_store=True,
    )
    assert app is not None


def test_empty_case_ids_deny(clock):
    principal = Principal("svc", "tenant-demo", ("workflow",), ("subj-demo-1",), ())
    assert not principal.allows_case("case-demo-42")
    services = AppServices(
        authenticator=TokenAuthenticator({"tok": principal}),
        collect=CollectEvidence(CaseSelectingStub(), MemoryEvidenceStore(), clock),
        list_evidence=ListEvidence(MemoryEvidenceStore()),
        mode="fixture",
    )
    client = TestClient(create_app(services))
    response = client.post(
        "/v1/evidence/collect",
        headers={"Authorization": "Bearer tok"},
        json={
            "case_id": "case-demo-42",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert response.status_code == 403


def test_star_case_ids_allow_all(clock):
    principal = Principal("svc", "tenant-demo", ("workflow",), ("subj-demo-1",), ("*",))
    assert principal.allows_case("case-any")
    store = MemoryEvidenceStore()
    services = AppServices(
        authenticator=TokenAuthenticator({"tok": principal}),
        collect=CollectEvidence(CaseSelectingStub(), store, clock),
        list_evidence=ListEvidence(store),
        mode="fixture",
    )
    client = TestClient(create_app(services))
    response = client.post(
        "/v1/evidence/collect",
        headers={"Authorization": "Bearer tok"},
        json={
            "case_id": "case-other-99",
            "case_revision": 1,
            "order_reference": "DEMO-ORDER-42",
        },
    )
    assert response.status_code == 200
