"""Real-peer case-api adapter rejects bad peers and never falls back."""

from __future__ import annotations

import json

import httpx
import pytest
from tests.conftest import OPERATOR

from sentinel_merchant_teams.adapters.case_api_http import HttpCaseApi
from sentinel_merchant_teams.adapters.identity_http import HttpIdentityMemberships
from sentinel_merchant_teams.application.errors import (
    ConfigurationError,
    PeerMalformedError,
    PeerUnauthorizedError,
    PeerUnavailableError,
)
from sentinel_merchant_teams.bootstrap import Settings, build_app
from sentinel_merchant_teams.domain.types import CONTRACT_VERSION, Principal


def _settings(**overrides) -> Settings:
    base = dict(
        mode="real-peers",
        tokens="t=p|tenant|operator|m|c",
        case_api_base_url="http://case.test",
        case_api_token="tok",
        identity_base_url="",
        identity_token="",
        contract_version=CONTRACT_VERSION,
    )
    base.update(overrides)
    return Settings(**base)


class _Transport(httpx.BaseTransport):
    def __init__(self, handler):
        self._handler = handler

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._handler(request)


def test_real_peers_requires_case_api_config():
    with pytest.raises(ConfigurationError):
        build_app(_settings(case_api_base_url="", case_api_token=""))


def test_real_peers_requires_database_url():
    with pytest.raises(PeerUnavailableError, match="MERCHANT_TEAMS_DATABASE_URL"):
        build_app(_settings())


def test_real_peers_identity_requires_token_when_base_url_set():
    with pytest.raises(ConfigurationError, match="IDENTITY_TOKEN"):
        build_app(_settings(identity_base_url="http://identity.test", identity_token=""))


def test_real_peers_identity_rejects_local_membership_writes(identity):
    from fastapi.testclient import TestClient
    from tests.conftest import TOKENS

    from sentinel_merchant_teams.adapters.auth import TokenAuthenticator
    from sentinel_merchant_teams.adapters.case_api_stub import StubCaseApi
    from sentinel_merchant_teams.adapters.clock import SystemClock
    from sentinel_merchant_teams.adapters.http_api import AppServices, create_app
    from sentinel_merchant_teams.adapters.storage_memory import MemoryStaffStore
    from sentinel_merchant_teams.application.staff import StaffService

    services = AppServices(
        authenticator=TokenAuthenticator(TOKENS),
        staff=StaffService(
            MemoryStaffStore(),
            StubCaseApi(mode="valid"),
            SystemClock(),
            identity,
            identity_authoritative=True,
        ),
        mode="real-peers",
    )
    client = TestClient(create_app(services))
    denied = client.post(
        "/v1/staff",
        headers={"Authorization": "Bearer operator-token"},
        json={
            "merchant_ref": "merchant-demo-1",
            "display_name": "Nope",
            "roles": ["viewer"],
        },
    )
    assert denied.status_code == 409
    assert denied.json()["code"] == "CONFLICT"


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


def test_http_identity_memberships_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    api = HttpIdentityMemberships(
        base_url="http://identity.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnavailableError):
        api.list_memberships(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            principal=OPERATOR,
        )


def test_http_identity_memberships_unauthorized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"code": "FORBIDDEN"})

    api = HttpIdentityMemberships(
        base_url="http://identity.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerUnauthorizedError):
        api.list_memberships(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            principal=OPERATOR,
        )


def test_http_identity_memberships_malformed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    api = HttpIdentityMemberships(
        base_url="http://identity.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    with pytest.raises(PeerMalformedError):
        api.list_memberships(
            tenant_id="tenant-demo",
            merchant_ref="merchant-demo-1",
            principal=OPERATOR,
        )


def test_http_identity_memberships_valid():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/merchant-memberships"
        assert request.url.params["tenant_id"] == "tenant-demo"
        assert request.url.params["merchant_ref"] == "merchant-demo-1"
        body = {
            "contract_version": CONTRACT_VERSION,
            "memberships": [
                {
                    "membership_id": "mm-1",
                    "assignment_id": "asg-1",
                    "user_id": "user-1",
                    "tenant_id": "tenant-demo",
                    "merchant_ref": "merchant-demo-1",
                    "display_name": "Projected",
                    "subroles": ["viewer", "operator"],
                    "status": "active",
                }
            ],
        }
        return httpx.Response(200, content=json.dumps(body).encode("utf-8"))

    api = HttpIdentityMemberships(
        base_url="http://identity.test",
        token="tok",
        client=httpx.Client(transport=_Transport(handler)),
    )
    rows = api.list_memberships(
        tenant_id="tenant-demo",
        merchant_ref="merchant-demo-1",
        principal=OPERATOR,
    )
    assert len(rows) == 1
    assert rows[0].subroles == ("viewer", "operator")
