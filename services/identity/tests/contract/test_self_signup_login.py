"""Merchant self-signup + email login signals (#154)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from tests.conftest import NEW_PASSWORD, auth_header

from sentinel_identity.application.rate_limit import LoginRateLimiter
from sentinel_identity.bootstrap import Settings, build_app
from sentinel_identity.domain.roles import CONTRACT_VERSION

MERCHANT = {
    "email": "Shop-Owner@Example.test",
    "password": NEW_PASSWORD,
    "display_name": "Shop Owner",
    "business_name": "Synthetic Spices Ltd",
    "preferred_language": "hi",
}


def test_merchant_register_creates_merchant_workspace(client: TestClient, store) -> None:
    response = client.post("/v1/auth/merchant/register", json=MERCHANT)
    assert response.status_code == 201, response.text
    body = response.json()
    assignment = body["assignment"]
    assert body["user"]["email"] == "shop-owner@example.test"
    assert body["user"]["email_verified_at"] is None
    assert body["user"]["preferred_language"] == "hi"
    assert body["business_name"] == "Synthetic Spices Ltd"
    assert assignment["role_id"] == "merchant"
    assert assignment["tenant_id"] == "tenant-demo"
    assert assignment["merchant_ref"].startswith("merchant-")
    assert assignment["scope_key"] == f"tenant:tenant-demo|merchant:{assignment['merchant_ref']}"

    me = client.get("/v1/auth/me", headers=auth_header(body["session_token"])).json()
    assert me["active_assignment"]["role_id"] == "merchant"
    assert "merchant.workspace.read" in me["permissions"]

    # Merchant-teams projection sees the new owner as admin of the new org only.
    members = client.get(
        "/v1/merchant-memberships",
        params={"tenant_id": "tenant-demo", "merchant_ref": assignment["merchant_ref"]},
        headers=auth_header(body["session_token"]),
    ).json()
    assert members["contract_version"] == CONTRACT_VERSION
    assert [m["subroles"] for m in members["memberships"]] == [["admin"]]

    audit = [e for e in store.list_audit() if e.action == "merchant.registered"]
    assert audit and audit[-1].details["business_name"] == "Synthetic Spices Ltd"

    # Email verification flow is the same as customer signup.
    verify = client.post(
        "/v1/auth/verify/request", json={}, headers=auth_header(body["session_token"])
    )
    assert verify.status_code == 202


def test_merchant_refs_are_unique(client: TestClient) -> None:
    first = client.post("/v1/auth/merchant/register", json=MERCHANT).json()
    second = client.post(
        "/v1/auth/merchant/register", json={**MERCHANT, "email": "other-shop@example.test"}
    ).json()
    assert first["assignment"]["merchant_ref"] != second["assignment"]["merchant_ref"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("merchant_ref", "merchant-demo-1"),
        ("tenant_id", "tenant-other"),
        ("role", "platform_admin"),
        ("roles", ["supervisor"]),
        ("role_id", "supervisor"),
        ("subject_refs", ["customer-1"]),
        ("subject", "customer-1"),
        ("account_type", "staff"),
        ("permissions", ["approval.decide"]),
    ],
)
def test_merchant_register_rejects_privileged_fields(
    client: TestClient, field: str, value: object
) -> None:
    response = client.post("/v1/auth/merchant/register", json={**MERCHANT, field: value})
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"
    login = client.post(
        "/v1/auth/login", json={"email": MERCHANT["email"], "password": NEW_PASSWORD}
    )
    assert login.json()["code"] == "ACCOUNT_NOT_FOUND"


@pytest.mark.parametrize(
    "patch",
    [{"business_name": "  "}, {"password": "short"}, {"display_name": ""}, {"email": ""}],
)
def test_merchant_register_validates_input(client: TestClient, patch: dict) -> None:
    response = client.post("/v1/auth/merchant/register", json={**MERCHANT, **patch})
    assert response.status_code == 422


def test_merchant_register_duplicate_email_matches_customer_conflict(
    client: TestClient,
) -> None:
    for path in ("/v1/auth/merchant/register", "/v1/auth/customer/register"):
        response = client.post(path, json={**MERCHANT, "email": "customer@example.test"})
        assert response.status_code == 409
        assert response.json()["code"] == "CONFLICT"
        assert response.json()["message"] == "Account already exists"


def test_login_unknown_email_vs_wrong_password(client: TestClient) -> None:
    unknown = client.post(
        "/v1/auth/login", json={"email": "nobody@example.test", "password": "whatever-1"}
    )
    assert unknown.status_code == 404
    assert unknown.json()["code"] == "ACCOUNT_NOT_FOUND"

    wrong = client.post(
        "/v1/auth/login", json={"email": "customer@example.test", "password": "wrong-pass"}
    )
    assert wrong.status_code == 401
    assert wrong.json()["code"] == "UNAUTHORIZED"
    assert wrong.json()["message"] == "Invalid credentials"


@pytest.mark.parametrize(
    "body", [{"email": "", "password": "x"}, {"email": "no-at-sign", "password": "x"}, {}]
)
def test_login_validates_input_before_account_lookup(client: TestClient, body: dict) -> None:
    response = client.post("/v1/auth/login", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"


def test_login_rate_limited_per_email(client: TestClient, demo_password: str) -> None:
    for _ in range(5):
        r = client.post(
            "/v1/auth/login", json={"email": "customer@example.test", "password": "wrong-pass"}
        )
        assert r.status_code == 401
    limited = client.post(
        "/v1/auth/login", json={"email": "customer@example.test", "password": demo_password}
    )
    assert limited.status_code == 429
    assert limited.json()["code"] == "RATE_LIMITED"


def test_login_rate_limited_per_ip_counts_unknown_emails(client: TestClient) -> None:
    headers = {"X-Forwarded-For": "203.0.113.7"}
    for i in range(20):
        r = client.post(
            "/v1/auth/login",
            json={"email": f"probe-{i}@example.test", "password": "whatever-1"},
            headers=headers,
        )
        assert r.status_code == 404
    limited = client.post(
        "/v1/auth/login",
        json={"email": "probe-x@example.test", "password": "whatever-1"},
        headers=headers,
    )
    assert limited.status_code == 429


class _Clock:
    def __init__(self) -> None:
        self.at = datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        return self.at


def test_rate_limiter_window_reset_and_bound() -> None:
    clock = _Clock()
    limiter = LoginRateLimiter(clock, max_per_email=2, max_per_ip=3, max_keys=4)
    assert limiter.record_failure(email="a@x.test", ip="1.1.1.1")
    assert limiter.record_failure(email="a@x.test", ip="1.1.1.1")
    assert limiter.is_limited(email="a@x.test", ip="1.1.1.1")
    assert not limiter.is_limited(email="a@x.test", ip="9.9.9.9")
    limiter.reset_email("a@x.test", ip="1.1.1.1")
    assert not limiter.is_limited(email="a@x.test", ip="1.1.1.1")
    assert limiter.record_failure(email="b@x.test", ip="1.1.1.1")
    assert limiter.is_limited(email="c@x.test", ip="1.1.1.1")
    clock.at += timedelta(minutes=16)
    assert not limiter.is_limited(email="c@x.test", ip="1.1.1.1")


def make_proxy_client(store, trusted=frozenset({"127.0.0.1"})) -> TestClient:
    return TestClient(
        build_app(
            Settings(
                mode="fixture",
                contract_version=CONTRACT_VERSION,
                database_url="",
                seed=False,
                accept_link_base="http://127.0.0.1:3000",
                trusted_proxies=trusted,
            ),
            store=store,
        ),
        client=("127.0.0.1", 50000),
    )


def probe(c: TestClient, email: str, ip: str | None = None, password="wrong-pass"):
    headers = {"X-Forwarded-For": ip} if ip is not None else {}
    return c.post("/v1/auth/login", json={"email": email, "password": password}, headers=headers)


def test_forwarded_ip_trusted_only_from_configured_proxy(store) -> None:
    trusted = make_proxy_client(store)
    for i in range(20):
        assert probe(trusted, f"p{i}@example.test", "198.51.100.1, 192.0.2.1").status_code == 404
    assert probe(trusted, "new@example.test", "192.0.2.1").status_code == 429
    assert probe(trusted, "new@example.test", "192.0.2.2").status_code == 404
    untrusted = make_proxy_client(store, trusted=frozenset())
    for i in range(20):
        assert probe(untrusted, f"p{i}@example.test", f"192.0.2.{i}").status_code == 404
    assert probe(untrusted, "new@example.test", "192.0.2.99").status_code == 429


@pytest.mark.parametrize("forwarded", [None, "garbage", "203.0.113.2, malformed"])
def test_proxy_without_valid_client_ip_does_not_lock_out_other_accounts(store, forwarded) -> None:
    client = make_proxy_client(store)
    for i in range(21):
        assert probe(client, f"p{i}@example.test", forwarded).status_code == 404


def test_email_attack_from_another_ip_cannot_lock_out_correct_password(
    store, demo_password
) -> None:
    client = make_proxy_client(store)
    for _ in range(5):
        assert probe(client, "customer@example.test", "192.0.2.1").status_code == 401
    assert probe(client, "customer@example.test", "192.0.2.1").status_code == 429
    assert probe(client, "customer@example.test", "192.0.2.2", demo_password).status_code == 200


def test_unknown_client_email_limit_still_allows_correct_password(store, demo_password) -> None:
    client = make_proxy_client(store)
    for _ in range(5):
        assert probe(client, "customer@example.test").status_code == 401
    assert probe(client, "customer@example.test").status_code == 429
    assert probe(client, "customer@example.test", password=demo_password).status_code == 200


def test_key_capacity_never_evicts_active_limits_and_prunes_expired() -> None:
    clock = _Clock()
    limiter = LoginRateLimiter(clock, max_per_email=2, max_keys=2)
    assert limiter.record_failure(email="victim@x.test", ip="192.0.2.1")
    assert limiter.record_failure(email="victim@x.test", ip="192.0.2.1")
    assert limiter.is_limited(email="new@x.test", ip="192.0.2.2")
    assert not limiter.record_failure(email="new@x.test", ip="192.0.2.2")
    assert limiter.is_limited(email="victim@x.test", ip="192.0.2.1")
    clock.at += timedelta(minutes=16)
    assert limiter.record_failure(email="new@x.test", ip="192.0.2.2")
    assert len(limiter._hits) == 2


def test_concurrent_failures_are_admitted_atomically() -> None:
    limiter = LoginRateLimiter(_Clock(), max_per_email=5)
    with ThreadPoolExecutor(max_workers=20) as workers:
        admitted = list(
            workers.map(
                lambda _: limiter.record_failure(email="a@x.test", ip="192.0.2.1"),
                range(100),
            )
        )
    assert sum(admitted) == 5
    assert limiter.is_limited(email="a@x.test", ip="192.0.2.1")


def test_trusted_proxy_defaults_require_explicit_configuration() -> None:
    assert not Settings.from_environ({}).trusted_proxies


def test_cli_preserves_socket_peer_for_application_proxy_validation(monkeypatch) -> None:
    from sentinel_identity import cli

    calls = []
    monkeypatch.setattr(cli, "build_app", lambda settings: object())
    monkeypatch.setattr(cli.uvicorn, "run", lambda *args, **kwargs: calls.append(kwargs))
    assert cli.main(["serve"]) == 0
    assert calls[0].get("proxy_headers") is False
