"""Identity session projection maps to Principal; HTTP peer fail-closed."""

from pathlib import Path

import httpx
import pytest

from sentinel_api.adapters.http.auth import CompositePrincipalResolver, TokenMap
from sentinel_api.adapters.identity.fixture import (
    FixtureIdentityPrincipalAdapter,
    principal_from_session_projection,
)
from sentinel_api.adapters.identity.http import HttpIdentityPrincipalAdapter, principal_from_me
from sentinel_api.bootstrap import build_app
from sentinel_api.config import Settings
from sentinel_api.domain.types import DomainError, Principal

MODULE_ROOT = Path(__file__).resolve().parents[2]


def test_principal_from_session_projection_ignores_merchant_refs():
    principal = principal_from_session_projection(
        {
            "principal_id": "customer-a",
            "tenant_id": "tenant-demo",
            "roles": ["customer"],
            "subject_refs": ["subject-a"],
            "case_ids": [],
            "merchant_refs": ["merchant-x"],
        }
    )
    assert principal == Principal(
        principal_id="customer-a",
        tenant_id="tenant-demo",
        roles=("customer",),
        subject_refs=("subject-a",),
        case_ids=(),
    )


def test_principal_from_me_maps_active_assignment():
    principal = principal_from_me(
        {
            "user": {"user_id": "user-op-1"},
            "active_assignment": {
                "tenant_id": "tenant-demo",
                "role_id": "operator",
                "subject_refs": ["subject-a"],
                "case_ids": ["case-1"],
            },
        }
    )
    assert principal == Principal(
        principal_id="user-op-1",
        tenant_id="tenant-demo",
        roles=("operator",),
        subject_refs=("subject-a",),
        case_ids=("case-1",),
    )


def test_principal_from_me_uses_merchant_ref_as_subject():
    principal = principal_from_me(
        {
            "user": {"user_id": "user-m-1"},
            "active_assignment": {
                "tenant_id": "tenant-demo",
                "role_id": "merchant",
                "merchant_ref": "merchant-demo-1",
            },
        }
    )
    assert principal.subject_refs == ("merchant-demo-1",)


def test_opaque_token_map_wins_when_present():
    identity = FixtureIdentityPrincipalAdapter.from_mapping(
        {
            "sess-op": {
                "principal_id": "operator-session",
                "tenant_id": "tenant-demo",
                "roles": ["operator"],
                "subject_refs": [],
                "case_ids": [],
            }
        }
    )
    tokens = TokenMap.from_mapping(
        {
            "sess-op": {
                "principal_id": "operator-opaque",
                "tenant_id": "tenant-demo",
                "roles": ["operator"],
                "subject_refs": [],
                "case_ids": [],
            },
            "tok-workflow": {
                "principal_id": "workflow-1",
                "tenant_id": "tenant-demo",
                "roles": ["workflow"],
                "subject_refs": [],
                "case_ids": ["*"],
            },
        }
    )
    resolver = CompositePrincipalResolver(identity=identity, tokens=tokens)
    asserted = resolver.resolve("Bearer sess-op")
    assert asserted.principal_id == "operator-opaque"
    service = resolver.resolve("Bearer tok-workflow")
    assert service.principal_id == "workflow-1"
    only_identity = CompositePrincipalResolver(
        identity=identity,
        tokens=TokenMap.from_mapping({}),
    )
    assert only_identity.resolve("Bearer sess-op").principal_id == "operator-session"


def test_composite_rejects_unknown_bearer():
    resolver = CompositePrincipalResolver(
        identity=FixtureIdentityPrincipalAdapter.from_mapping({}),
        tokens=TokenMap.from_mapping({}),
    )
    try:
        resolver.resolve("Bearer missing")
        raise AssertionError("expected DomainError")
    except DomainError as exc:
        assert exc.http_status == 401
        assert exc.code == "UNAUTHORIZED"


def test_http_identity_me_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/auth/me"
        assert request.headers["Authorization"] == "Bearer sess-live"
        return httpx.Response(
            200,
            json={
                "user": {"user_id": "user-live"},
                "active_assignment": {
                    "tenant_id": "tenant-demo",
                    "role_id": "supervisor",
                    "subject_refs": ["*"],
                    "case_ids": [],
                },
                "permissions": [],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://identity.test")
    adapter = HttpIdentityPrincipalAdapter("http://identity.test", client=client)
    principal = adapter.project("sess-live")
    assert principal == Principal(
        principal_id="user-live",
        tenant_id="tenant-demo",
        roles=("supervisor",),
        subject_refs=("*",),
        case_ids=(),
    )


@pytest.mark.parametrize(
    "status,body",
    [
        (500, {"code": "DOWN"}),
        (200, {"not": "me"}),
        (200, {"user": {"user_id": "u"}, "active_assignment": {"role_id": "operator"}}),
    ],
)
def test_http_identity_fail_closed(status, body):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://identity.test")
    adapter = HttpIdentityPrincipalAdapter("http://identity.test", client=client)
    with pytest.raises(DomainError) as exc:
        adapter.project("sess-bad")
    assert exc.value.code == "UNAUTHORIZED"
    assert exc.value.http_status == 401


def test_http_identity_unauthorized_falls_through_to_token_map():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"code": "UNAUTHORIZED"})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://identity.test")
    identity = HttpIdentityPrincipalAdapter("http://identity.test", client=client)
    tokens = TokenMap.from_mapping(
        {
            "tok-workflow": {
                "principal_id": "workflow-1",
                "tenant_id": "tenant-demo",
                "roles": ["workflow"],
                "subject_refs": [],
                "case_ids": ["*"],
            }
        }
    )
    resolver = CompositePrincipalResolver(identity=identity, tokens=tokens)
    assert resolver.resolve("Bearer tok-workflow").principal_id == "workflow-1"
    with pytest.raises(DomainError) as exc:
        resolver.resolve("Bearer sess-unknown")
    assert exc.value.code == "UNAUTHORIZED"


def test_http_identity_unavailable_fail_closed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://identity.test")
    adapter = HttpIdentityPrincipalAdapter("http://identity.test", client=client)
    with pytest.raises(DomainError) as exc:
        adapter.project("sess-live")
    assert exc.value.message == "Identity peer unavailable"


def test_real_peers_without_identity_url_is_token_map_only(engine):
    tokens = TokenMap.from_path(MODULE_ROOT / "fixtures" / "auth_tokens.json")
    settings = Settings(
        mode="real-peers",
        host="127.0.0.1",
        workflow_base_url="http://127.0.0.1:1",
        evidence_base_url="http://127.0.0.1:1",
        ledger_base_url="http://127.0.0.1:1",
        verifier_base_url="http://127.0.0.1:1",
        service_token="live-service-token",
        identity_base_url="",
    )
    app = build_app(settings, engine=engine, tokens=tokens)
    assert isinstance(app.state.tokens, TokenMap)
    with pytest.raises(DomainError) as exc:
        app.state.tokens.resolve("Bearer sess-operator-1")
    assert exc.value.code == "UNAUTHORIZED"


def test_real_peers_wires_http_identity(engine, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "user": {"user_id": "user-op"},
                "active_assignment": {
                    "tenant_id": "tenant-demo",
                    "role_id": "operator",
                },
                "permissions": [],
            },
        )

    transport = httpx.MockTransport(handler)

    class _Client(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(
        "sentinel_api.adapters.identity.http.httpx.Client",
        _Client,
    )
    tokens = TokenMap.from_path(MODULE_ROOT / "fixtures" / "auth_tokens.json")
    settings = Settings(
        mode="real-peers",
        host="127.0.0.1",
        workflow_base_url="http://127.0.0.1:1",
        evidence_base_url="http://127.0.0.1:1",
        ledger_base_url="http://127.0.0.1:1",
        verifier_base_url="http://127.0.0.1:1",
        service_token="live-service-token",
        identity_base_url="http://identity.test",
    )
    app = build_app(settings, engine=engine, tokens=tokens)
    assert isinstance(app.state.tokens, CompositePrincipalResolver)
    principal = app.state.tokens.resolve("Bearer sess-from-identity")
    assert principal.principal_id == "user-op"
    assert principal.roles == ("operator",)
    # Service opaque token still resolves without depending on identity body.
    workflow = app.state.tokens.resolve("Bearer tok-workflow")
    assert "workflow" in workflow.roles
