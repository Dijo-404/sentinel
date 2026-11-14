"""Real-peer adapters and bootstrap fail closed; no fixture fallback."""

from __future__ import annotations

import httpx
import pytest
from tests.stubs import StubCaseApi, StubEvidence, StubLedger, StubPolicy

from sentinel_merchant_refunds.adapters.http_peers import (
    HttpCaseApiClient,
    HttpEvidenceClient,
    HttpLedgerClient,
    HttpPolicyClient,
)
from sentinel_merchant_refunds.bootstrap import build_app
from sentinel_merchant_refunds.domain.errors import PeerError, PeerUnavailableError
from sentinel_merchant_refunds.domain.types import Principal, ProposalRequest


@pytest.fixture
def peers():
    evidence = StubEvidence()
    evidence.seed_demo()
    return StubCaseApi(), evidence, StubPolicy(), StubLedger()


def test_fixture_mode_requires_injected_peers():
    with pytest.raises(PeerUnavailableError):
        build_app(mode="fixture", store=object())


def test_real_peers_refuses_demo_bearer(monkeypatch):
    monkeypatch.setenv("MERCHANT_REFUNDS_PEER_BEARER_TOKEN", "token-merchant-refunds-demo")
    monkeypatch.setenv("CASE_API_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("EVIDENCE_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("POLICY_BASE_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("LEDGER_BASE_URL", "http://127.0.0.1:9")
    with pytest.raises(PeerUnavailableError, match="MERCHANT_REFUNDS_PEER_BEARER_TOKEN"):
        build_app(mode="real-peers", store=object())


def test_real_peers_refuses_default_memory_store(peers):
    case_api, evidence, policy, ledger = peers
    with pytest.raises(PeerUnavailableError, match="durable store"):
        build_app(
            mode="real-peers",
            case_api=case_api,
            evidence=evidence,
            policy=policy,
            ledger=ledger,
        )


def test_real_peers_env_mode_refuses_default_memory_store(monkeypatch, peers):
    monkeypatch.setenv("MERCHANT_REFUNDS_MODE", "real-peers")
    monkeypatch.delenv("MERCHANT_REFUNDS_DATABASE_URL", raising=False)
    case_api, evidence, policy, ledger = peers
    with pytest.raises(PeerUnavailableError, match="durable store"):
        build_app(
            case_api=case_api,
            evidence=evidence,
            policy=policy,
            ledger=ledger,
        )


def test_http_case_api_unavailable():
    client = HttpCaseApiClient("http://127.0.0.1:9", token="t")
    principal = Principal(
        principal_id="p",
        tenant_id="t1",
        merchant_ref="m1",
        roles=["merchant_staff"],
    )
    with pytest.raises(PeerUnavailableError):
        client.get_case(principal, "case-demo-42")


def test_http_peers_surface_error_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN", "message": "nope"})

    transport = httpx.MockTransport(handler)
    principal = Principal(
        principal_id="p",
        tenant_id="t1",
        merchant_ref="m1",
        roles=["merchant_staff"],
    )

    case = HttpCaseApiClient("http://peer.test", token="t")
    case._client = httpx.Client(transport=transport, base_url="http://peer.test")
    with pytest.raises(PeerError) as exc:
        case.get_case(principal, "case-demo-42")
    assert exc.value.http_status == 403

    evidence = HttpEvidenceClient("http://peer.test", token="t")
    evidence._client = httpx.Client(transport=transport, base_url="http://peer.test")
    with pytest.raises(PeerError):
        evidence.get_case_evidence(principal, "case-demo-42")

    policy = HttpPolicyClient("http://peer.test", token="t")
    policy._client = httpx.Client(transport=transport, base_url="http://peer.test")
    with pytest.raises(PeerError):
        policy.evaluate(
            principal,
            payload={"action": "REQUEST_REFUND"},
            evidence=[{"evidence_id": "e"}],
        )

    ledger = HttpLedgerClient("http://peer.test", token="t")
    ledger._client = httpx.Client(transport=transport, base_url="http://peer.test")
    with pytest.raises(PeerError):
        ledger.create_proposal(
            principal,
            ProposalRequest(operation_key="k", payload={}, action_digest="d"),
        )


def test_http_ledger_malformed_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    transport = httpx.MockTransport(handler)
    ledger = HttpLedgerClient("http://peer.test", token="t")
    ledger._client = httpx.Client(transport=transport, base_url="http://peer.test")
    principal = Principal(
        principal_id="p",
        tenant_id="t1",
        merchant_ref="m1",
        roles=["merchant_staff"],
    )
    with pytest.raises(PeerError) as exc:
        ledger.get_action(principal, "action-1")
    assert exc.value.code == "MALFORMED_PEER"
