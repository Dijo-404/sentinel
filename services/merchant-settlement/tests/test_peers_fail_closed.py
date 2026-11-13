"""Real-peer adapters reject bad peers and never fall back to fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from sentinel_merchant_settlement.adapters.evidence_http import HttpEvidence
from sentinel_merchant_settlement.adapters.evidence_stub import StubEvidence
from sentinel_merchant_settlement.adapters.provider_http import HttpPaymentProvider
from sentinel_merchant_settlement.adapters.provider_stub import StubPaymentProvider
from sentinel_merchant_settlement.adapters.store_memory import MemoryFindingStore
from sentinel_merchant_settlement.application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_settlement.bootstrap import Settings, build_app
from sentinel_merchant_settlement.domain.types import Principal

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"
PRINCIPAL = Principal(
    "op-demo",
    "demo-tenant-a",
    ("operator",),
    ("merchant:demo-merchant-1",),
    ("*",),
)


class _Transport(httpx.BaseTransport):
    def __init__(self, handler):
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def _settings(**overrides) -> Settings:
    base = dict(
        mode="real-peers",
        principals_path=CONTRACTS / "principals.json",
        contract_version="sentinel.task-contracts.v1",
        evidence_base_url="",
        evidence_token="",
        provider_base_url="",
        provider_token="",
    )
    base.update(overrides)
    return Settings(**base)


def test_real_peers_requires_peer_config():
    with pytest.raises(ConfigurationError):
        build_app(_settings())


def test_http_provider_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    provider = HttpPaymentProvider(
        base_url="http://provider.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnavailableError):
        provider.load_world(
            principal=PRINCIPAL,
            tenant_id="demo-tenant-a",
            merchant_ref="demo-merchant-1",
            period_start="2026-11-01T00:00:00Z",
            period_end="2026-11-30T23:59:59Z",
            order_refs=("ORDER-OK",),
            transaction_refs=("TXN-OK",),
        )


def test_http_provider_unauthorized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN"})

    provider = HttpPaymentProvider(
        base_url="http://provider.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnauthorizedError):
        provider.load_world(
            principal=PRINCIPAL,
            tenant_id="demo-tenant-a",
            merchant_ref="demo-merchant-1",
            period_start="2026-11-01T00:00:00Z",
            period_end="2026-11-30T23:59:59Z",
            order_refs=("ORDER-OK",),
            transaction_refs=("TXN-OK",),
        )


def test_http_provider_malformed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    provider = HttpPaymentProvider(
        base_url="http://provider.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerMalformedError):
        provider.load_world(
            principal=PRINCIPAL,
            tenant_id="demo-tenant-a",
            merchant_ref="demo-merchant-1",
            period_start="2026-11-01T00:00:00Z",
            period_end="2026-11-30T23:59:59Z",
            order_refs=("ORDER-OK",),
            transaction_refs=("TXN-OK",),
        )


def test_http_evidence_fail_closed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    evidence = HttpEvidence(
        base_url="http://evidence.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnavailableError):
        evidence.load_world(
            principal=PRINCIPAL,
            tenant_id="demo-tenant-a",
            merchant_ref="demo-merchant-1",
            order_refs=("ORDER-OK",),
            transaction_refs=("TXN-OK",),
        )


def test_http_provider_valid_path_no_fixture_fallback():
    payments = {
        "payments": [
            {
                "transaction_ref": "TXN-OK",
                "order_reference": "ORDER-OK",
                "subject_ref": "subj-demo-1",
                "status": "CAPTURED",
                "amount_minor": 150000,
                "currency": "INR",
                "expected_fee_minor": 5000,
                "occurred_at": "2026-11-02T10:00:00Z",
            }
        ]
    }
    order = {
        "order_reference": "ORDER-OK",
        "subject_ref": "subj-demo-1",
        "fulfilled_order_count": 1,
        "merchant_confirmed_duplicate": False,
        "paid": True,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/transactions":
            return httpx.Response(200, content=json.dumps(payments).encode())
        if request.url.path.startswith("/v1/orders/"):
            return httpx.Response(200, content=json.dumps(order).encode())
        return httpx.Response(404)

    provider = HttpPaymentProvider(
        base_url="http://provider.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    world = provider.load_world(
        principal=PRINCIPAL,
        tenant_id="demo-tenant-a",
        merchant_ref="demo-merchant-1",
        period_start="2026-11-01T00:00:00Z",
        period_end="2026-11-30T23:59:59Z",
        order_refs=("ORDER-OK",),
        transaction_refs=("TXN-OK",),
    )
    assert len(world.payments) == 1
    assert world.payments[0].transaction_ref == "TXN-OK"


def test_import_surfaces_peer_unavailable_without_fixture_fallback(
    fixture_batch_dict: dict,
):
    app = build_app(
        _settings(
            evidence_base_url="http://evidence.test",
            evidence_token="tok",
            provider_base_url="http://provider.test",
            provider_token="tok",
        ),
        evidence=StubEvidence(case="unavailable"),
        provider=StubPaymentProvider(),
        store=MemoryFindingStore(),
    )
    client = TestClient(app)
    response = client.post(
        "/v1/settlements/batches",
        headers={"Authorization": "Bearer operator-demo-token"},
        json=fixture_batch_dict,
    )
    assert response.status_code == 503
    assert response.json()["code"] == "PEER_UNAVAILABLE"
    # Capabilities still label real-peers mode; no silent fixture success.
    assert client.get("/v1/capabilities").json()["mode"] == "real-peers"
