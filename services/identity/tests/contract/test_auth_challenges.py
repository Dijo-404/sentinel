"""Contract: verify-email, MFA challenge, forgot/reset password (sandbox)."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from tests.conftest import NEW_PASSWORD, auth_header, login

from sentinel_identity.adapters.clock import SystemClock
from sentinel_identity.adapters.seed import load_seed_users
from sentinel_identity.adapters.storage_memory import MemoryIdentityStore
from sentinel_identity.application.errors import ConfigurationError
from sentinel_identity.application.security import (
    CHALLENGE_CODE_LENGTH,
    MAX_CHALLENGE_ATTEMPTS,
)
from sentinel_identity.bootstrap import Settings, build_app


def _peek_code(store: MemoryIdentityStore, *, user_id: str, purpose: str) -> str:
    code = store.peek_auth_sandbox_code(user_id=user_id, purpose=purpose)
    assert code, f"missing sandbox code for {purpose}"
    return code


def _fixture_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "mode": "fixture",
        "contract_version": "sentinel.task-contracts.v1",
        "database_url": "",
        "seed": False,
        "accept_link_base": "http://127.0.0.1:3000",
        "expose_sandbox_codes": False,
        "sandbox": False,
        "sandbox_token": "",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_verify_request_confirm_marks_email_verified(
    client: TestClient, store: MemoryIdentityStore, demo_password: str
) -> None:
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    user_id = session["user"]["user_id"]

    requested = client.post("/v1/auth/verify/request", headers=headers, json={})
    assert requested.status_code == 202, requested.text
    body = requested.json()
    assert "sandbox_code" not in body
    assert body.get("status") == "accepted"

    code = _peek_code(store, user_id=user_id, purpose="email_verify")
    assert len(code) >= CHALLENGE_CODE_LENGTH
    confirm = client.post(
        "/v1/auth/verify/confirm",
        headers=headers,
        json={"code": code},
    )
    assert confirm.status_code == 200, confirm.text
    user = store.get_user(user_id)
    assert user is not None
    assert user.email_verified_at is not None


def test_verify_confirm_rejects_bad_code(client: TestClient, demo_password: str) -> None:
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    client.post("/v1/auth/verify/request", headers=headers, json={})
    bad = client.post(
        "/v1/auth/verify/confirm",
        headers=headers,
        json={"code": "AAAAAAAA"},
    )
    assert bad.status_code == 400
    assert bad.json()["code"] == "INVALID_CHALLENGE"


def test_mfa_challenge_verify_sets_session_flag(
    client: TestClient, store: MemoryIdentityStore, demo_password: str
) -> None:
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    user_id = session["user"]["user_id"]

    challenged = client.post("/v1/auth/mfa/challenge", headers=headers, json={})
    assert challenged.status_code == 202, challenged.text
    assert "sandbox_code" not in challenged.json()

    code = _peek_code(store, user_id=user_id, purpose="mfa")
    verified = client.post(
        "/v1/auth/mfa/verify",
        headers=headers,
        json={"code": code},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json().get("mfa_verified") is True

    token_hash_sessions = [
        s for s in store.sessions.values() if s.revoked_at is None and s.user_id == user_id
    ]
    assert token_hash_sessions
    assert token_hash_sessions[-1].mfa_verified_at is not None


def test_forgot_never_enumerates_email(client: TestClient, demo_password: str) -> None:
    known = client.post(
        "/v1/auth/password/forgot",
        json={"email": "customer@example.test"},
    )
    unknown = client.post(
        "/v1/auth/password/forgot",
        json={"email": "nobody-here@example.test"},
    )
    assert known.status_code == 202
    assert unknown.status_code == 202
    assert known.json() == unknown.json()
    assert "sandbox_code" not in known.json()
    assert "sandbox_code" not in unknown.json()
    # Sandbox demo: identical hint for known + unknown (no email enum).
    assert known.json().get("sandbox_hint") == (
        "use GET /v1/auth/sandbox/password-reset-code with X-Identity-Sandbox-Token"
    )
    assert demo_password


def test_password_reset_success_and_invalid(
    client: TestClient, store: MemoryIdentityStore, demo_password: str
) -> None:
    forgot = client.post(
        "/v1/auth/password/forgot",
        json={"email": "customer@example.test"},
    )
    assert forgot.status_code == 202
    user = store.get_user_by_email("customer@example.test")
    assert user is not None
    code = _peek_code(store, user_id=user.user_id, purpose="password_reset")

    bad = client.post(
        "/v1/auth/password/reset",
        json={
            "email": "customer@example.test",
            "code": "AAAAAAAA",
            "new_password": NEW_PASSWORD,
        },
    )
    assert bad.status_code == 400
    assert bad.json()["code"] == "INVALID_CHALLENGE"

    unknown = client.post(
        "/v1/auth/password/reset",
        json={
            "email": "ghost@example.test",
            "code": code,
            "new_password": NEW_PASSWORD,
        },
    )
    assert unknown.status_code == 400
    assert unknown.json()["code"] == "INVALID_CHALLENGE"
    assert unknown.json()["message"] == bad.json()["message"]

    ok = client.post(
        "/v1/auth/password/reset",
        json={
            "email": "customer@example.test",
            "code": code,
            "new_password": NEW_PASSWORD,
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json().get("status") == "reset"

    old = client.post(
        "/v1/auth/login",
        json={"email": "customer@example.test", "password": demo_password},
    )
    assert old.status_code == 401
    fresh = login(client, "customer@example.test", NEW_PASSWORD)
    assert fresh["session_token"]


def test_expose_sandbox_codes_opt_in_only(demo_password: str) -> None:
    store = MemoryIdentityStore()
    load_seed_users(store, SystemClock())
    app = build_app(_fixture_settings(expose_sandbox_codes=True), store=store)
    client = TestClient(app)
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])

    verify = client.post("/v1/auth/verify/request", headers=headers, json={})
    assert verify.status_code == 202
    code = verify.json().get("sandbox_code")
    assert isinstance(code, str)
    assert len(code) >= CHALLENGE_CODE_LENGTH

    mfa = client.post("/v1/auth/mfa/challenge", headers=headers, json={})
    assert mfa.status_code == 202
    assert isinstance(mfa.json().get("sandbox_code"), str)

    forgot = client.post(
        "/v1/auth/password/forgot",
        json={"email": "customer@example.test"},
    )
    assert forgot.status_code == 202
    assert isinstance(forgot.json().get("sandbox_code"), str)

    ghost = client.post(
        "/v1/auth/password/forgot",
        json={"email": "ghost@example.test"},
    )
    assert ghost.status_code == 202
    assert "sandbox_code" not in ghost.json()


def test_challenge_routes_require_bearer(client: TestClient) -> None:
    assert client.post("/v1/auth/verify/request", json={}).status_code == 401
    assert client.post("/v1/auth/verify/confirm", json={"code": "ABCD2345"}).status_code == 401
    assert client.post("/v1/auth/mfa/challenge", json={}).status_code == 401
    assert client.post("/v1/auth/mfa/verify", json={"code": "ABCD2345"}).status_code == 401


def test_expired_challenge_rejected(
    client: TestClient, store: MemoryIdentityStore, demo_password: str
) -> None:
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    user_id = session["user"]["user_id"]
    client.post("/v1/auth/verify/request", headers=headers, json={})
    code = _peek_code(store, user_id=user_id, purpose="email_verify")
    challenge = next(
        c
        for c in store.auth_challenges.values()
        if c.user_id == user_id and c.challenge_type == "email_verify"
    )
    store.save_auth_challenge(
        replace(challenge, expires_at=challenge.created_at - timedelta(seconds=1))
    )
    response = client.post(
        "/v1/auth/verify/confirm",
        headers=headers,
        json={"code": code},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_CHALLENGE"


def test_consumed_challenge_reuse_rejected(
    client: TestClient, store: MemoryIdentityStore, demo_password: str
) -> None:
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    user_id = session["user"]["user_id"]
    client.post("/v1/auth/verify/request", headers=headers, json={})
    code = _peek_code(store, user_id=user_id, purpose="email_verify")
    first = client.post("/v1/auth/verify/confirm", headers=headers, json={"code": code})
    assert first.status_code == 200, first.text
    second = client.post("/v1/auth/verify/confirm", headers=headers, json={"code": code})
    assert second.status_code == 400
    assert second.json()["code"] == "INVALID_CHALLENGE"


def test_challenge_locks_after_max_failed_attempts(
    client: TestClient, store: MemoryIdentityStore, demo_password: str
) -> None:
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    user_id = session["user"]["user_id"]
    client.post("/v1/auth/verify/request", headers=headers, json={})
    code = _peek_code(store, user_id=user_id, purpose="email_verify")
    for _ in range(MAX_CHALLENGE_ATTEMPTS):
        bad = client.post(
            "/v1/auth/verify/confirm",
            headers=headers,
            json={"code": "ZZZZZZZZ"},
        )
        assert bad.status_code == 400
    locked = next(
        c
        for c in store.auth_challenges.values()
        if c.user_id == user_id and c.challenge_type == "email_verify"
    )
    assert locked.attempt_count == MAX_CHALLENGE_ATTEMPTS
    assert locked.consumed_at is not None
    still = client.post("/v1/auth/verify/confirm", headers=headers, json={"code": code})
    assert still.status_code == 400


def test_build_app_refuses_real_peers_with_expose() -> None:
    with pytest.raises(ConfigurationError, match="EXPOSE_SANDBOX_CODES"):
        build_app(
            _fixture_settings(
                mode="real-peers",
                expose_sandbox_codes=True,
                database_url="postgresql+psycopg://identity:identity@127.0.0.1:5432/identity",
            )
        )


def test_sandbox_latest_code_404_when_flag_off(demo_password: str) -> None:
    store = MemoryIdentityStore()
    load_seed_users(store, SystemClock())
    app = build_app(_fixture_settings(sandbox=False), store=store)
    client = TestClient(app)
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    client.post("/v1/auth/verify/request", headers=headers, json={})
    assert (
        store.peek_auth_sandbox_code(user_id=session["user"]["user_id"], purpose="email_verify")
        is None
    )
    missing = client.get(
        "/v1/auth/sandbox/latest-code",
        params={"purpose": "email_verify"},
        headers=headers,
    )
    assert missing.status_code == 404


def test_sandbox_latest_code_returns_code_when_flag_on(
    client: TestClient, store: MemoryIdentityStore, demo_password: str
) -> None:
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    user_id = session["user"]["user_id"]
    client.post("/v1/auth/verify/request", headers=headers, json={})
    peek = store.peek_auth_sandbox_code(user_id=user_id, purpose="email_verify")
    assert peek
    inbox = client.get(
        "/v1/auth/sandbox/latest-code",
        params={"purpose": "email_verify"},
        headers=headers,
    )
    assert inbox.status_code == 200, inbox.text
    assert inbox.json() == {"code": peek}

    client.post("/v1/auth/mfa/challenge", headers=headers, json={})
    mfa_peek = store.peek_auth_sandbox_code(user_id=user_id, purpose="mfa")
    mfa_inbox = client.get(
        "/v1/auth/sandbox/latest-code",
        params={"purpose": "mfa"},
        headers=headers,
    )
    assert mfa_inbox.status_code == 200
    assert mfa_inbox.json() == {"code": mfa_peek}


def test_sandbox_password_reset_code_token_gated(
    client: TestClient, store: MemoryIdentityStore, demo_password: str
) -> None:
    forgot = client.post(
        "/v1/auth/password/forgot",
        json={"email": "customer@example.test"},
    )
    assert forgot.status_code == 202
    user = store.get_user_by_email("customer@example.test")
    assert user is not None
    peek = store.peek_auth_sandbox_code(user_id=user.user_id, purpose="password_reset")
    assert peek

    bad_token = client.get(
        "/v1/auth/sandbox/password-reset-code",
        params={"email": "customer@example.test"},
        headers={"X-Identity-Sandbox-Token": "wrong"},
    )
    assert bad_token.status_code == 404

    unknown = client.get(
        "/v1/auth/sandbox/password-reset-code",
        params={"email": "ghost@example.test"},
        headers={"X-Identity-Sandbox-Token": "test-sandbox-token"},
    )
    assert unknown.status_code == 404
    assert unknown.json()["code"] == bad_token.json()["code"]

    ok = client.get(
        "/v1/auth/sandbox/password-reset-code",
        params={"email": "customer@example.test"},
        headers={"X-Identity-Sandbox-Token": "test-sandbox-token"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json() == {"code": peek}
    assert demo_password


def test_real_peers_allows_sandbox_flag_not_expose(demo_password: str) -> None:
    store = MemoryIdentityStore()
    load_seed_users(store, SystemClock())
    app = build_app(
        _fixture_settings(
            mode="real-peers",
            sandbox=True,
            sandbox_token="demo-token",
            database_url="postgresql+psycopg://identity:identity@127.0.0.1:5432/identity",
        ),
        store=store,
    )
    client = TestClient(app)
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])
    requested = client.post("/v1/auth/verify/request", headers=headers, json={})
    assert requested.status_code == 202
    assert "sandbox_code" not in requested.json()
    inbox = client.get(
        "/v1/auth/sandbox/latest-code",
        params={"purpose": "email_verify"},
        headers=headers,
    )
    assert inbox.status_code == 200
    assert isinstance(inbox.json().get("code"), str)
