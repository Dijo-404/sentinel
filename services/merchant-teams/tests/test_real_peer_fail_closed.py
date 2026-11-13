"""Real-peer case-api adapter rejects bad peers and never falls back."""

from __future__ import annotations

import json

import httpx
import pytest
from tests.conftest import OPERATOR

from sentinel_merchant_teams.adapters.case_api_http import HttpCaseApi
from sentinel_merchant_teams.application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_teams.bootstrap import Settings, build_app
from sentinel_merchant_teams.domain.types import CONTRACT_VERSION, Principal


class _Transport(httpx.BaseTransport):
    def __init__(self, handler):
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def test_real_peers_requires_case_api_config():
    with pytest.raises(ConfigurationError):
        build_app(
            Settings(
                mode="real-peers",
                tokens="t=p|tenant|operator|m|c",
                case_api_base_url="",
                case_api_token="",
                contract_version=CONTRACT_VERSION,
            )
        )


def test_http_case_api_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    api = HttpCaseApi(
        base_url="http://case.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnavailableError):
        api.get_case("case-demo-42", principal=OPERATOR)


def test_http_case_api_unauthorized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN"})

    api = HttpCaseApi(
        base_url="http://case.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnauthorizedError):
        api.get_case("case-demo-42", principal=OPERATOR)


def test_http_case_api_malformed_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    api = HttpCaseApi(
        base_url="http://case.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerMalformedError):
        api.get_case("case-demo-42", principal=OPERATOR)


def test_http_case_api_valid():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/cases/case-demo-42"
        body = {
            "contract_version": CONTRACT_VERSION,
            "case_id": "case-demo-42",
            "revision": 2,
            "status": "INVESTIGATING",
            "language": "en-IN",
            "intent": "DUPLICATE_PAYMENT",
            "evidence_ids": [],
        }
        return httpx.Response(200, content=json.dumps(body).encode("utf-8"))

    api = HttpCaseApi(
        base_url="http://case.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    snap = api.get_case(
        "case-demo-42",
        principal=Principal(
            "svc", "tenant-demo", ("operator",), ("merchant-demo-1",), ("case-demo-42",)
        ),
    )
    assert snap.revision == 2


def test_case_activity_surfaces_peer_failure(service, cases):
    from tests.conftest import OPERATOR

    from sentinel_merchant_teams.application.errors import PeerUnavailableError

    cases.mode = "unavailable"
    service.create(
        OPERATOR,
        merchant_ref="merchant-demo-1",
        display_name="Ada",
        roles=["operator"],
        staff_id="staff-peer",
    )
    with pytest.raises(PeerUnavailableError):
        service.record_activity(
            OPERATOR,
            "staff-peer",
            kind="CASE_VIEW",
            subject_ref="case-demo-42",
            summary="Should fail",
        )
