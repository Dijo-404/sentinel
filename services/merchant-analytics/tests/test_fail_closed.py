"""Unavailable/unauthorized/malformed peers fail closed; no fixture fallback."""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from constants import TOKENS, WINDOW
from sentinel_merchant_analytics.adapters.case_http import HttpCaseApi
from sentinel_merchant_analytics.adapters.evidence_http import HttpEvidence
from sentinel_merchant_analytics.adapters.fixture_peers import FixtureCaseApi, FixtureEvidence
from sentinel_merchant_analytics.application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_analytics.bootstrap import Settings, build_app
from sentinel_merchant_analytics.domain.types import Principal

PRINCIPAL = Principal(
    "op-1", "tenant-demo", ("operator",), ("subj-demo-1",), ("*",), ("merchant-demo-1",)
)


class _Transport(httpx.BaseTransport):
    def __init__(self, handler):
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def _app_with(case_behavior: str, evidence_behavior: str) -> TestClient:
    settings = Settings(
        mode="fixture",
        tokens=TOKENS,
        case_api_base_url="",
        case_api_token="",
        evidence_base_url="",
        evidence_token="",
        contract_version="sentinel.task-contracts.v1",
    )
    app = build_app(
        settings,
        case_api=FixtureCaseApi(case_behavior),
        evidence=FixtureEvidence(evidence_behavior),
    )
    return TestClient(app)


def test_case_unavailable_fail_closed():
    client = _app_with("unavailable", "valid")
    response = client.get(
        "/v1/merchants/merchant-demo-1/metrics",
        params=WINDOW,
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "PEER_UNAVAILABLE"


def test_evidence_unavailable_fail_closed():
    client = _app_with("valid", "unavailable")
    response = client.get(
        "/v1/merchants/merchant-demo-1/metrics",
        params=WINDOW,
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "PEER_UNAVAILABLE"


def test_case_unauthorized_fail_closed():
    client = _app_with("unauthorized_or_out_of_scope", "valid")
    response = client.get(
        "/v1/merchants/merchant-demo-1/metrics",
        params=WINDOW,
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "PEER_UNAUTHORIZED"


def test_evidence_malformed_fail_closed():
    client = _app_with("valid", "malformed")
    response = client.get(
        "/v1/merchants/merchant-demo-1/metrics",
        params=WINDOW,
        headers={"Authorization": "Bearer operator-token"},
    )
    assert response.status_code == 502
    assert response.json()["code"] == "PEER_MALFORMED"


def test_real_peers_requires_urls():
    with pytest.raises(ConfigurationError):
        build_app(
            Settings(
                mode="real-peers",
                tokens=TOKENS,
                case_api_base_url="",
                case_api_token="",
                evidence_base_url="",
                evidence_token="",
                contract_version="sentinel.task-contracts.v1",
            )
        )


def test_http_case_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    api = HttpCaseApi(
        base_url="http://case.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnavailableError):
        api.list_merchant_cases(
            PRINCIPAL,
            merchant_ref="merchant-demo-1",
            window_start=WINDOW["window_start"],
            window_end=WINDOW["window_end"],
        )


def test_http_case_unauthorized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN"})

    api = HttpCaseApi(
        base_url="http://case.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnauthorizedError):
        api.list_merchant_cases(
            PRINCIPAL,
            merchant_ref="merchant-demo-1",
            window_start=WINDOW["window_start"],
            window_end=WINDOW["window_end"],
        )


def test_http_evidence_malformed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    api = HttpEvidence(
        base_url="http://evidence.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerMalformedError):
        api.list_refund_facts(PRINCIPAL, case_ids=["case-m-01"])


def test_http_case_valid_no_fixture_fallback():
    payload = {
        "cases": [
            {
                "case_id": "case-live-1",
                "merchant_ref": "merchant-demo-1",
                "status": "VERIFIED_RESOLVED",
                "intent": "DUPLICATE_PAYMENT",
                "opened_at": "2026-11-02T10:00:00Z",
                "closed_at": "2026-11-02T11:00:00Z",
                "evidence_ids": [],
                "currency": "INR",
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps(payload).encode("utf-8"))

    api = HttpCaseApi(
        base_url="http://case.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    rows = api.list_merchant_cases(
        PRINCIPAL,
        merchant_ref="merchant-demo-1",
        window_start=WINDOW["window_start"],
        window_end=WINDOW["window_end"],
    )
    assert len(rows) == 1
    assert rows[0].case_id == "case-live-1"
