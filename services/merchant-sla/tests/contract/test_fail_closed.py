"""Real-peer adapter and fixture stubs fail closed; no silent fixture fallback."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from tests.conftest import PRINCIPALS, T0
from tests.stubs import malformed, unauthorized_or_out_of_scope, unavailable

from sentinel_merchant_sla.adapters.case_api_http import HttpCaseApi
from sentinel_merchant_sla.adapters.clock import FixedClock
from sentinel_merchant_sla.adapters.memory_store import MemorySlaStore
from sentinel_merchant_sla.application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_sla.application.service import MerchantSlaService
from sentinel_merchant_sla.bootstrap import Settings, build_app, build_case_api, load_settings
from sentinel_merchant_sla.contracts import Principal

PRINCIPAL = Principal(
    principal_id="op-merchant-demo",
    tenant_id="demo-tenant-a",
    roles=("operator", "merchant_ops"),
    subject_refs=("subject-demo-42",),
    case_ids=("case-demo-42",),
    merchant_refs=("merchant-demo-a",),
)


class _Transport(httpx.BaseTransport):
    def __init__(self, handler):
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def test_real_peers_requires_case_api_config():
    with pytest.raises(ConfigurationError):
        build_case_api(
            Settings(
                mode="real-peers",
                principals_path=PRINCIPALS,
                case_api_base_url="",
                case_api_token="",
            )
        )


def test_real_peers_build_app_rejects_missing_peer():
    with pytest.raises(ConfigurationError):
        build_app(
            settings=Settings(
                mode="real-peers",
                principals_path=PRINCIPALS,
                case_api_base_url="",
                case_api_token="",
            )
        )


def test_http_case_api_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    peer = HttpCaseApi(
        base_url="http://case-api.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnavailableError):
        peer.get_case("case-demo-42", PRINCIPAL)


def test_http_case_api_unauthorized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN"})

    peer = HttpCaseApi(
        base_url="http://case-api.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnauthorizedError):
        peer.get_case("case-demo-42", PRINCIPAL)


def test_http_case_api_malformed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    peer = HttpCaseApi(
        base_url="http://case-api.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerMalformedError):
        peer.get_case("case-demo-42", PRINCIPAL)


@pytest.mark.parametrize(
    ("peer_factory", "exc_type"),
    [
        (unavailable, PeerUnavailableError),
        (malformed, PeerMalformedError),
        (unauthorized_or_out_of_scope, PeerUnauthorizedError),
    ],
)
def test_service_create_task_fails_closed_on_bad_peer(peer_factory, exc_type):
    svc = MerchantSlaService(
        store=MemorySlaStore(),
        clock=FixedClock(T0),
        case_api=peer_factory(),
    )
    policy = svc.upsert_policy(
        PRINCIPAL,
        {
            "tenant_id": "demo-tenant-a",
            "merchant_ref": "merchant-demo-a",
            "respond_within_seconds": 60,
            "resolve_within_seconds": 120,
        },
    )
    with pytest.raises(exc_type):
        svc.create_task(
            PRINCIPAL,
            {"case_id": "case-demo-42", "policy_id": policy.policy_id},
        )


def test_load_settings_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MERCHANT_SLA_MODE", raising=False)
    settings = load_settings(principals_path=PRINCIPALS)
    assert settings.mode == "fixture"
