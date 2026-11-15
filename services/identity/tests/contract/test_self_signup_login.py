"""Merchant self-signup + email login signals (#154)."""

from __future__ import annotations

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
    limiter.record_failure(email="a@x.test", ip="1.1.1.1")
    limiter.record_failure(email="a@x.test", ip="1.1.1.1")
    assert limiter.is_limited(email="a@x.test", ip="9.9.9.9")
    limiter.reset_email("a@x.test")
    assert not limiter.is_limited(email="a@x.test", ip="9.9.9.9")
    limiter.record_failure(email="b@x.test", ip="1.1.1.1")
    assert limiter.is_limited(email="c@x.test", ip="1.1.1.1")  # ip limit 3
    clock.at += timedelta(minutes=16)
    assert not limiter.is_limited(email="c@x.test", ip="1.1.1.1")
    for i in range(10):
        limiter.record_failure(email=f"{i}@x.test", ip="")
    assert len(limiter._hits) <= 4


def test_forwarded_ip_trusted_only_from_configured_proxy(store) -> None:
    def make(trusted: frozenset[str]) -> TestClient:
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
            )
        )

    def probe(c: TestClient, ip: str, i: int) -> int:
        return c.post(
            "/v1/auth/login",
            json={"email": f"p{ip}-{i}@example.test", "password": "whatever-1"},
            headers={"X-Forwarded-For": f"198.51.100.1, {ip}"},
        ).status_code

    trusted = make(frozenset({"testclient"}))
    assert all(probe(trusted, "192.0.2.1", i) == 404 for i in range(20))
    assert probe(trusted, "192.0.2.1", 99) == 429
    assert probe(trusted, "192.0.2.2", 0) == 404  # separate client bucket

    untrusted = make(frozenset())
    assert all(probe(untrusted, f"192.0.2.{i + 10}", i) == 404 for i in range(20))
    assert probe(untrusted, "192.0.2.99", 0) == 429  # spoofed XFF ignored
