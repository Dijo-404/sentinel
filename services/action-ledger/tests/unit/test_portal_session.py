"""Portal session resolution via identity /v1/auth/me (fake transport). Fail closed."""

from __future__ import annotations

import httpx
import pytest

from sentinel_action_ledger.adapters.auth_tokens import TokenPrincipalMap, demo_principals
from sentinel_action_ledger.adapters.portal_session import (
    HttpPortalSessionResolver,
    PortalSessionPrincipalMap,
    principal_map_from_environ,
)
from sentinel_action_ledger.domain.errors import (
    ForbiddenError,
    PeerUnavailableError,
    UnauthorizedError,
)

BASE = "http://identity.test"


def me_body(role="supervisor", *, user_status="active", tenant="tenant-demo"):
    return {
        "user": {"user_id": "usr-sup-7", "status": user_status, "account_type": "staff"},
        "workspaces": [],
        "active_assignment": {
            "assignment_id": "asg-1",
            "tenant_id": tenant,
            "role_id": role,
            "scope_key": "tenant",
            "status": "active",
        },
        "permissions": [],
    }


def resolver(handler) -> tuple[PortalSessionPrincipalMap, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(record))
    sessions = HttpPortalSessionResolver(BASE, client=client)
    return PortalSessionPrincipalMap(demo_principals(), sessions), seen


def ok(body):
    return lambda _r: httpx.Response(200, json=body)


def test_supervisor_session_maps_to_human_supervisor():
    auth, seen = resolver(ok(me_body()))
    principal = auth.resolve("Bearer sess-abc")
    assert principal.principal_id == "usr-sup-7"
    assert principal.tenant_id == "tenant-demo"
    assert principal.roles == ("supervisor",)
    assert principal.case_ids == ("*",)
    assert str(seen[0].url) == f"{BASE}/v1/auth/me"
    assert seen[0].headers["authorization"] == "Bearer sess-abc"


def test_operator_session_maps_to_read_only_operator():
    auth, _ = resolver(ok(me_body("operator")))
    assert auth.resolve("Bearer sess-op").roles == ("operator",)


REJECTED_ROLES = [
    "customer",
    "merchant",
    "platform_admin",
    "risk_officer",
    "workflow",
    "dispatcher",
    "verifier",
]


@pytest.mark.parametrize("role", REJECTED_ROLES)
def test_other_portal_roles_rejected(role):
    auth, _ = resolver(ok(me_body(role)))
    with pytest.raises(ForbiddenError):
        auth.resolve("Bearer sess-x")


@pytest.mark.parametrize("status", ["suspended", "deactivated", "pending"])
def test_inactive_user_forbidden(status):
    auth, _ = resolver(ok(me_body(user_status=status)))
    with pytest.raises(ForbiddenError):
        auth.resolve("Bearer sess-x")


def test_revoked_assignment_forbidden():
    body = me_body()
    body["active_assignment"]["status"] = "revoked"
    auth, _ = resolver(ok(body))
    with pytest.raises(ForbiddenError):
        auth.resolve("Bearer sess-x")


def test_no_active_assignment_forbidden():
    body = me_body()
    body["active_assignment"] = None
    auth, _ = resolver(ok(body))
    with pytest.raises(ForbiddenError):
        auth.resolve("Bearer sess-x")


def test_identity_403_forbidden():
    auth, _ = resolver(lambda _r: httpx.Response(403, json={"code": "FORBIDDEN"}))
    with pytest.raises(ForbiddenError):
        auth.resolve("Bearer sess-x")


@pytest.mark.parametrize("status", [500, 502, 503])
def test_identity_5xx_is_peer_unavailable(status):
    auth, _ = resolver(lambda _r: httpx.Response(status))
    with pytest.raises(PeerUnavailableError) as exc:
        auth.resolve("Bearer sess-x")
    assert exc.value.http_status == 503


def test_identity_unreachable_is_peer_unavailable():
    def boom(request):
        raise httpx.ConnectTimeout("timeout", request=request)

    auth, _ = resolver(boom)
    with pytest.raises(PeerUnavailableError):
        auth.resolve("Bearer sess-x")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, json={"code": "UNAUTHORIZED"}),
        httpx.Response(404),
        httpx.Response(200, content=b"not json"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={"user": {"status": "active"}}),
        httpx.Response(200, json={**me_body(), "user": {"status": "active", "user_id": ""}}),
        httpx.Response(200, json={**me_body(), "active_assignment": "supervisor"}),
    ],
)
def test_non_200_or_malformed_me_unauthorized(response):
    auth, _ = resolver(lambda _r: response)
    with pytest.raises(UnauthorizedError):
        auth.resolve("Bearer sess-x")


def test_static_token_wins_without_calling_identity():
    auth, seen = resolver(ok(me_body("operator")))
    principal = auth.resolve("Bearer tok-supervisor")
    assert principal.principal_id == "supervisor-demo"
    assert seen == []


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer ", "Bearer   "])
def test_missing_bearer_never_calls_identity(header):
    auth, seen = resolver(ok(me_body()))
    with pytest.raises(UnauthorizedError):
        auth.resolve(header)
    assert seen == []


@pytest.mark.parametrize("value", [None, "", "  "])
def test_feature_off_when_env_unset(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("LEDGER_IDENTITY_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("LEDGER_IDENTITY_BASE_URL", value)
    auth = principal_map_from_environ(demo_principals())
    assert type(auth) is TokenPrincipalMap
    with pytest.raises(UnauthorizedError):
        auth.resolve("Bearer sess-abc")


def test_feature_on_when_env_set(monkeypatch):
    monkeypatch.setenv("LEDGER_IDENTITY_BASE_URL", BASE)
    assert isinstance(principal_map_from_environ(demo_principals()), PortalSessionPrincipalMap)
