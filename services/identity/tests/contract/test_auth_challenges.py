"""Contract: verify-email, MFA challenge, forgot/reset password (sandbox)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from tests.conftest import NEW_PASSWORD, auth_header, login

from sentinel_identity.adapters.clock import SystemClock
from sentinel_identity.adapters.seed import load_seed_users
from sentinel_identity.adapters.storage_memory import MemoryIdentityStore
from sentinel_identity.bootstrap import Settings, build_app


def _peek_code(store: MemoryIdentityStore, *, user_id: str, purpose: str) -> str:
    code = store.peek_auth_sandbox_code(user_id=user_id, purpose=purpose)
    assert code, f"missing sandbox code for {purpose}"
    return code


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
        json={"code": "000000"},
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
    # unused demo_password keeps fixture signature consistent with siblings
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
            "code": "000000",
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
    app = build_app(
        Settings(
            mode="fixture",
            contract_version="sentinel.task-contracts.v1",
            database_url="",
            seed=False,
            accept_link_base="http://127.0.0.1:3000",
            expose_sandbox_codes=True,
        ),
        store=store,
    )
    client = TestClient(app)
    session = login(client, "customer@example.test", demo_password)
    headers = auth_header(session["session_token"])

    verify = client.post("/v1/auth/verify/request", headers=headers, json={})
    assert verify.status_code == 202
    assert isinstance(verify.json().get("sandbox_code"), str)
    assert len(verify.json()["sandbox_code"]) == 6

    mfa = client.post("/v1/auth/mfa/challenge", headers=headers, json={})
    assert mfa.status_code == 202
    assert isinstance(mfa.json().get("sandbox_code"), str)

    forgot = client.post(
        "/v1/auth/password/forgot",
        json={"email": "customer@example.test"},
    )
    assert forgot.status_code == 202
    assert isinstance(forgot.json().get("sandbox_code"), str)

    # unknown email still 202; must not leak a code
    ghost = client.post(
        "/v1/auth/password/forgot",
        json={"email": "ghost@example.test"},
    )
    assert ghost.status_code == 202
    assert "sandbox_code" not in ghost.json()


def test_challenge_routes_require_bearer(client: TestClient) -> None:
    assert client.post("/v1/auth/verify/request", json={}).status_code == 401
    assert client.post("/v1/auth/verify/confirm", json={"code": "123456"}).status_code == 401
    assert client.post("/v1/auth/mfa/challenge", json={}).status_code == 401
    assert client.post("/v1/auth/mfa/verify", json={"code": "123456"}).status_code == 401
