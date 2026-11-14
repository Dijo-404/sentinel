"""Wave 3 live peer checks: identity me / notifications / workspaces / forgot."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any, TypedDict

DEFAULT_IDENTITY_URL = "http://127.0.0.1:8012"

# fixtures/seed_users.json — not assembly matrix tok-customer.
SEED_CUSTOMER_EMAIL = "customer@example.test"
SEED_CUSTOMER_USER_ID = "11111111-1111-1111-1111-111111111101"
SEED_NOTIFICATION_ID = "11111111-1111-1111-1111-111111111301"
SEED_CUSTOMER_DISPLAY_NAME = "Demo Customer"
SEED_CUSTOMER_PREFERRED_LANGUAGE = "en"
DEFAULT_DEMO_PASSWORD = "x"
UNKNOWN_FORGOT_EMAIL = "nobody-wave3-verify@example.test"


class CheckResult(TypedDict, total=False):
    name: str
    ok: bool
    status_code: int
    detail: str


class VerifyReport(TypedDict, total=False):
    status: str
    checks: list[CheckResult]
    reason_code: str


def assert_me_body(body: Any) -> None:
    """Fail unless seeded customer profile fields are present."""
    if not isinstance(body, dict):
        raise AssertionError("me body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"me error code={body.get('code')!r}")
    user = body.get("user")
    if not isinstance(user, dict):
        raise AssertionError("me.user missing (seed / session required)")
    if user.get("email") != SEED_CUSTOMER_EMAIL:
        raise AssertionError(
            f"me.user.email want {SEED_CUSTOMER_EMAIL!r} got {user.get('email')!r}"
        )
    if user.get("user_id") != SEED_CUSTOMER_USER_ID:
        raise AssertionError(
            f"me.user.user_id want {SEED_CUSTOMER_USER_ID!r} got {user.get('user_id')!r}"
        )
    if user.get("display_name") != SEED_CUSTOMER_DISPLAY_NAME:
        raise AssertionError(
            f"me.user.display_name want {SEED_CUSTOMER_DISPLAY_NAME!r} "
            f"got {user.get('display_name')!r}"
        )
    if user.get("preferred_language") != SEED_CUSTOMER_PREFERRED_LANGUAGE:
        raise AssertionError(
            f"me.user.preferred_language want {SEED_CUSTOMER_PREFERRED_LANGUAGE!r} "
            f"got {user.get('preferred_language')!r} (seed required)"
        )


def assert_notifications_body(body: Any) -> None:
    """Fail unless seeded notification is present."""
    if not isinstance(body, dict):
        raise AssertionError("notifications body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"notifications error code={body.get('code')!r}")
    items = body.get("notifications")
    if not isinstance(items, list) or not items:
        raise AssertionError("notifications list empty or missing (seed required)")
    ids = {row.get("notification_id") for row in items if isinstance(row, dict)}
    if SEED_NOTIFICATION_ID not in ids:
        raise AssertionError(
            f"seed notification {SEED_NOTIFICATION_ID!r} not in list {sorted(ids)!r}"
        )


def assert_workspaces_body(body: Any) -> None:
    """Fail unless at least one workspace assignment is present."""
    if not isinstance(body, dict):
        raise AssertionError("workspaces body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"workspaces error code={body.get('code')!r}")
    items = body.get("workspaces")
    if not isinstance(items, list) or not items:
        raise AssertionError("workspaces list empty or missing (seed required)")
    roles = {row.get("role_id") for row in items if isinstance(row, dict)}
    if "customer" not in roles:
        raise AssertionError(f"customer workspace missing; roles={sorted(r for r in roles if r)!r}")


def assert_forgot_accepted(status: int, body: Any) -> None:
    """Fail unless forgot returns HTTP 202 with non-enumerating accepted body."""
    if status != 202:
        raise AssertionError(f"forgot want HTTP 202 got {status}; body={body!r}")
    if not isinstance(body, dict):
        raise AssertionError("forgot body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"forgot error code={body.get('code')!r}")
    if body.get("status") != "accepted":
        raise AssertionError(f"forgot status want 'accepted' got {body.get('status')!r}")


def assert_forgot_no_enumeration(
    known_status: int,
    known_body: Any,
    unknown_status: int,
    unknown_body: Any,
) -> None:
    """Known and unknown emails must share the same public 202 shape (no enum)."""
    assert_forgot_accepted(known_status, known_body)
    assert_forgot_accepted(unknown_status, unknown_body)
    if not isinstance(known_body, dict) or not isinstance(unknown_body, dict):
        raise AssertionError("forgot bodies must be JSON objects")
    # When sandbox codes are off, shapes must match. If expose is on, known may
    # include sandbox_code — still refuse any existence-revealing error codes.
    known_keys = set(known_body) - {"sandbox_code"}
    unknown_keys = set(unknown_body) - {"sandbox_code"}
    if known_keys != unknown_keys:
        raise AssertionError(
            f"forgot enumeration risk: known keys {sorted(known_keys)!r} "
            f"!= unknown keys {sorted(unknown_keys)!r}"
        )
    if known_body.get("status") != unknown_body.get("status"):
        raise AssertionError("forgot status differs for known vs unknown email")


def _request_json(
    url: str,
    *,
    method: str = "GET",
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> tuple[int, Any]:
    headers = {"Accept": "application/json"}
    data: bytes | None = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            status = getattr(resp, "status", 200)
            return int(status), json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            body: Any = json.loads(raw) if raw else {"message": str(exc)}
        except json.JSONDecodeError:
            body = {"message": raw or str(exc)}
        return int(exc.code), body


def _resolve_session_token(identity_base: str, env: Mapping[str, str]) -> str:
    """Prefer VERIFY_IDENTITY_TOKEN (session); else login seeded customer.

    Never use assembly matrix ``tok-*`` — identity requires hashed session tokens.
    """
    existing = (env.get("VERIFY_IDENTITY_TOKEN") or "").strip()
    if existing:
        if existing.startswith("tok-"):
            raise AssertionError(
                "VERIFY_IDENTITY_TOKEN looks like matrix tok-*; "
                "use identity login session_token instead"
            )
        return existing
    email = (env.get("VERIFY_IDENTITY_EMAIL") or SEED_CUSTOMER_EMAIL).strip()
    password = (
        env.get("VERIFY_IDENTITY_PASSWORD")
        or env.get("IDENTITY_DEMO_PASSWORD")
        or DEFAULT_DEMO_PASSWORD
    )
    status, body = _request_json(
        f"{identity_base}/v1/auth/login",
        method="POST",
        payload={"email": email, "password": password},
    )
    if status != 200 or not isinstance(body, dict):
        raise AssertionError(f"login failed status={status} body={body!r}")
    token = body.get("session_token")
    if not isinstance(token, str) or not token.strip():
        raise AssertionError("login missing session_token (seed / peers required)")
    if token.startswith("tok-"):
        raise AssertionError("login returned matrix-shaped tok-* token; refuse")
    return token


def verify_wave3(env: Mapping[str, str] | None = None) -> VerifyReport:
    """Hit identity auth surfaces; require seeded me/notifications/workspaces + forgot 202.

    Session: ``VERIFY_IDENTITY_TOKEN`` or login with seeded customer password.
    Fails closed without seed / peers down. No real money.
    """
    env = env or {}
    identity_base = (
        env.get("VERIFY_IDENTITY_URL")
        or env.get("CORE_ASSEMBLY_IDENTITY_URL")
        or DEFAULT_IDENTITY_URL
    ).rstrip("/")

    checks: list[CheckResult] = []

    try:
        session_token = _resolve_session_token(identity_base, env)
    except Exception as exc:  # noqa: BLE001 — surface connect/login as check failure
        return {
            "status": "FAIL",
            "checks": [
                {
                    "name": "identity.auth.session",
                    "ok": False,
                    "status_code": 0,
                    "detail": f"session resolve failed: {exc}",
                }
            ],
            "reason_code": "WAVE3_VERIFY_FAILED",
        }

    checks.append(
        {
            "name": "identity.auth.session",
            "ok": True,
            "status_code": 200,
            "detail": "ok",
        }
    )

    def run_get(name: str, path: str, assert_body) -> None:
        try:
            status, body = _request_json(
                f"{identity_base}{path}",
                token=session_token,
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(
                {
                    "name": name,
                    "ok": False,
                    "status_code": 0,
                    "detail": f"request failed: {exc}",
                }
            )
            return
        if status != 200:
            checks.append(
                {
                    "name": name,
                    "ok": False,
                    "status_code": status,
                    "detail": f"want HTTP 200 got {status}; body={body!r}",
                }
            )
            return
        try:
            assert_body(body)
        except AssertionError as exc:
            checks.append(
                {
                    "name": name,
                    "ok": False,
                    "status_code": status,
                    "detail": str(exc),
                }
            )
            return
        checks.append({"name": name, "ok": True, "status_code": status, "detail": "ok"})

    run_get("identity.auth.me", "/v1/auth/me", assert_me_body)
    run_get(
        "identity.auth.notifications",
        "/v1/auth/notifications",
        assert_notifications_body,
    )
    run_get(
        "identity.auth.workspaces",
        "/v1/auth/workspaces",
        assert_workspaces_body,
    )

    try:
        known_status, known_body = _request_json(
            f"{identity_base}/v1/auth/password/forgot",
            method="POST",
            payload={"email": SEED_CUSTOMER_EMAIL},
        )
        unknown_status, unknown_body = _request_json(
            f"{identity_base}/v1/auth/password/forgot",
            method="POST",
            payload={"email": UNKNOWN_FORGOT_EMAIL},
        )
        assert_forgot_no_enumeration(known_status, known_body, unknown_status, unknown_body)
        checks.append(
            {
                "name": "identity.auth.password.forgot",
                "ok": True,
                "status_code": 202,
                "detail": "ok",
            }
        )
    except Exception as exc:  # noqa: BLE001
        checks.append(
            {
                "name": "identity.auth.password.forgot",
                "ok": False,
                "status_code": 0,
                "detail": str(exc),
            }
        )

    if all(c.get("ok") for c in checks):
        return {"status": "PASS", "checks": checks}
    return {
        "status": "FAIL",
        "checks": checks,
        "reason_code": "WAVE3_VERIFY_FAILED",
    }
