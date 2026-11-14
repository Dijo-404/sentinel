"""Real-peer adapter rejects bad peers and never falls back to fixtures."""

from __future__ import annotations

import json

import httpx
import pytest

from sentinel_evidence.adapters.provider_http import HttpPaymentProvider
from sentinel_evidence.application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_evidence.bootstrap import Settings, build_app
from sentinel_evidence.domain.types import Principal

PRINCIPAL = Principal("svc", "tenant-demo", ("workflow",), ("subj-demo-1",), ("case-demo-42",))


class _Transport(httpx.BaseTransport):
    def __init__(self, handler):
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def test_real_peers_requires_provider_config():
    with pytest.raises(ConfigurationError):
        build_app(
            Settings(
                mode="real-peers",
                database_url=None,
                schema="evidence",
                tokens="t=p|tenant|workflow|s|c",
                provider_base_url="",
                provider_token="",
                ttl_seconds=60,
                contract_version="sentinel.task-contracts.v1",
            ),
            use_memory_store=True,
        )


def test_http_provider_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    client = httpx.Client(transport=_Transport(handler))
    provider = HttpPaymentProvider(
        base_url="http://provider.test",
        token="tok",
        client=client,
    )
    with pytest.raises(PeerUnavailableError):
        provider.fetch_snapshot(order_reference="DEMO-ORDER-42", principal=PRINCIPAL)


def test_http_provider_unauthorized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN"})

    provider = HttpPaymentProvider(
        base_url="http://provider.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnauthorizedError):
        provider.fetch_snapshot(order_reference="DEMO-ORDER-42", principal=PRINCIPAL)


def test_http_provider_malformed_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    provider = HttpPaymentProvider(
        base_url="http://provider.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerMalformedError):
        provider.fetch_snapshot(order_reference="DEMO-ORDER-42", principal=PRINCIPAL)


def test_http_provider_valid_path_no_fixture_fallback():
    """Successful real-peer path uses HTTP payloads only."""

    payments = {
        "payments": [
            {
                "transaction_ref": "TXN-A",
                "order_reference": "DEMO-ORDER-42",
                "subject_ref": "subj-demo-1",
                "status": "CAPTURED",
                "amount_minor": 150000,
                "currency": "INR",
            }
        ]
    }
    order = {
        "order_reference": "DEMO-ORDER-42",
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
        if request.url.path == "/v1/refunds":
            return httpx.Response(200, content=json.dumps({"refunds": []}).encode())
        return httpx.Response(404)

    provider = HttpPaymentProvider(
        base_url="http://provider.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    snapshot = provider.fetch_snapshot(order_reference="DEMO-ORDER-42", principal=PRINCIPAL)
    assert len(snapshot.payments) == 1
    assert snapshot.order.order_reference == "DEMO-ORDER-42"
    assert snapshot.order_payload == json.dumps(order).encode()


def test_http_provider_uses_bare_order_path():
    """Collect derives bare ids; HTTP adapter must query that key, not a subject prefix."""

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.path == "/v1/transactions":
            return httpx.Response(
                200,
                content=json.dumps(
                    {
                        "payments": [
                            {
                                "transaction_ref": "TXN-A",
                                "order_reference": "DEMO-ORDER-42",
                                "subject_ref": "subj-demo-1",
                                "status": "CAPTURED",
                                "amount_minor": 150000,
                                "currency": "INR",
                            }
                        ]
                    }
                ).encode(),
            )
        if request.url.path == "/v1/orders/DEMO-ORDER-42":
            return httpx.Response(
                200,
                content=json.dumps(
                    {
                        "order_reference": "DEMO-ORDER-42",
                        "subject_ref": "subj-demo-1",
                        "fulfilled_order_count": 1,
                        "merchant_confirmed_duplicate": False,
                        "paid": True,
                    }
                ).encode(),
            )
        if request.url.path == "/v1/refunds":
            return httpx.Response(200, content=json.dumps({"refunds": []}).encode())
        return httpx.Response(404)

    provider = HttpPaymentProvider(
        base_url="http://provider.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    provider.fetch_snapshot(order_reference="DEMO-ORDER-42", principal=PRINCIPAL)
    assert any("/v1/orders/DEMO-ORDER-42" in url for url in seen)
    assert any("order_reference=DEMO-ORDER-42" in url for url in seen)
    assert not any("subject-a" in url for url in seen)
