"""Wave 5 live peer checks: admin identity / policy / merchants / AI / evals / obs."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any, TypedDict

DEFAULT_IDENTITY_URL = "http://127.0.0.1:8012"
DEFAULT_POLICY_URL = "http://127.0.0.1:8005"
DEFAULT_MERCHANT_TEAMS_URL = "http://127.0.0.1:8034"
DEFAULT_PLATFORM_AI_URL = "http://127.0.0.1:8036"
DEFAULT_EVALS_URL = "http://127.0.0.1:8031"
DEFAULT_OBSERVABILITY_URL = "http://127.0.0.1:8033"

# Identity admin: session login (not matrix tok-*). Peer-local admin tokens below.
SEED_ADMIN_EMAIL = "admin@example.test"
DEFAULT_DEMO_PASSWORD = "x"
DEFAULT_POLICY_TOKEN = "tok-platform-admin"
DEFAULT_MERCHANT_TEAMS_TOKEN = "platform-admin-token"
DEFAULT_PLATFORM_AI_TOKEN = "admin-token"
DEFAULT_EVALS_TOKEN = "admin-token"
DEFAULT_OBSERVABILITY_TOKEN = "admin-token"

SEED_TENANT_ID = "tenant-demo"
SEED_POLICY_ID = "demo-policy-v1"
SEED_MERCHANT_REF = "merchant-demo-1"
SEED_MODEL_ID = "model-sandbox-1"
SEED_INTEGRATION_ID = "integration-sandbox-1"
SEED_EVAL_RUN_ID = "eval-sandbox-1"
SEED_SIGNAL_ID = "sig-seed-request-handle"


class CheckResult(TypedDict, total=False):
    name: str
    ok: bool
    status_code: int
    detail: str


class VerifyReport(TypedDict, total=False):
    status: str
    checks: list[CheckResult]
    reason_code: str


def assert_health_body(body: Any) -> None:
    """Fail unless health payload reports ok."""
    if not isinstance(body, dict):
        raise AssertionError("health body must be a JSON object")
    if body.get("status") != "ok":
        raise AssertionError(f"health status want 'ok' got {body.get('status')!r}")


def assert_roles_body(body: Any) -> None:
    """Fail unless platform_admin appears in human_roles."""
    if not isinstance(body, dict):
        raise AssertionError("roles body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"roles error code={body.get('code')!r}")
    roles = body.get("human_roles")
    if not isinstance(roles, list) or not roles:
        raise AssertionError("human_roles empty or missing (seed required)")
    if "platform_admin" not in roles:
        raise AssertionError(f"platform_admin missing; human_roles={sorted(roles)!r}")


def assert_tenants_body(body: Any) -> None:
    """Fail unless seeded tenant-demo is present."""
    if not isinstance(body, dict):
        raise AssertionError("tenants body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"tenants error code={body.get('code')!r}")
    items = body.get("tenants")
    if not isinstance(items, list) or not items:
        raise AssertionError("tenants list empty or missing (seed required)")
    ids = {row.get("tenant_id") for row in items if isinstance(row, dict)}
    if SEED_TENANT_ID not in ids:
        raise AssertionError(f"seed tenant {SEED_TENANT_ID!r} not in list {sorted(ids)!r}")


def assert_policies_body(body: Any) -> None:
    """Fail unless demo-policy-v1 catalog row is present."""
    if not isinstance(body, dict):
        raise AssertionError("policies body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"policies error code={body.get('code')!r}")
    items = body.get("policies")
    if not isinstance(items, list) or not items:
        raise AssertionError("policies list empty or missing (catalog seed required)")
    ids = {row.get("policy_id") for row in items if isinstance(row, dict)}
    if SEED_POLICY_ID not in ids:
        raise AssertionError(f"seed policy {SEED_POLICY_ID!r} not in list {sorted(ids)!r}")


def assert_merchants_body(body: Any) -> None:
    """Fail unless seeded merchant-demo-1 is present."""
    if not isinstance(body, dict):
        raise AssertionError("merchants body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"merchants error code={body.get('code')!r}")
    items = body.get("merchants")
    if not isinstance(items, list) or not items:
        raise AssertionError("merchants list empty or missing (seed required)")
    refs = {row.get("merchant_ref") for row in items if isinstance(row, dict)}
    if SEED_MERCHANT_REF not in refs:
        raise AssertionError(f"seed merchant {SEED_MERCHANT_REF!r} not in list {sorted(refs)!r}")


def assert_config_body(body: Any) -> None:
    """Fail unless seeded platform-ai model config is present."""
    if not isinstance(body, dict):
        raise AssertionError("config body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"config error code={body.get('code')!r}")
    models = body.get("models")
    if not isinstance(models, list) or not models:
        raise AssertionError("config.models empty or missing (seed required)")
    ids = {row.get("model_id") for row in models if isinstance(row, dict)}
    if SEED_MODEL_ID not in ids:
        raise AssertionError(f"seed model {SEED_MODEL_ID!r} not in list {sorted(ids)!r}")
    if "kill_switch" not in body:
        raise AssertionError("config.kill_switch missing")


def assert_integrations_body(body: Any) -> None:
    """Fail unless seeded platform-ai integration is present."""
    if not isinstance(body, dict):
        raise AssertionError("integrations body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"integrations error code={body.get('code')!r}")
    items = body.get("integrations")
    if not isinstance(items, list) or not items:
        raise AssertionError("integrations list empty or missing (seed required)")
    ids = {row.get("integration_id") for row in items if isinstance(row, dict)}
    if SEED_INTEGRATION_ID not in ids:
        raise AssertionError(
            f"seed integration {SEED_INTEGRATION_ID!r} not in list {sorted(ids)!r}"
        )


def assert_reports_body(body: Any) -> None:
    """Fail unless seeded eval RunReport is present."""
    if not isinstance(body, dict):
        raise AssertionError("reports body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"reports error code={body.get('code')!r}")
    items = body.get("reports")
    if not isinstance(items, list) or not items:
        raise AssertionError("reports list empty or missing (seed required)")
    ids = {row.get("run_id") for row in items if isinstance(row, dict)}
    if SEED_EVAL_RUN_ID not in ids:
        raise AssertionError(f"seed report {SEED_EVAL_RUN_ID!r} not in list {sorted(ids)!r}")


def assert_signals_body(body: Any) -> None:
    """Fail unless seeded observability signal is present."""
    if not isinstance(body, dict):
        raise AssertionError("signals body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"signals error code={body.get('code')!r}")
    if body.get("financial_audit") is not False:
        raise AssertionError(
            f"signals.financial_audit want False got {body.get('financial_audit')!r}"
        )
    items = body.get("signals")
    if not isinstance(items, list) or not items:
        raise AssertionError("signals list empty or missing (seed required)")
    ids = {row.get("signal_id") for row in items if isinstance(row, dict)}
    if SEED_SIGNAL_ID not in ids:
        raise AssertionError(f"seed signal {SEED_SIGNAL_ID!r} not in list {sorted(ids)!r}")


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


def _resolve_admin_session(identity_base: str, env: Mapping[str, str]) -> str:
    """Prefer VERIFY_IDENTITY_ADMIN_TOKEN; else login seeded platform_admin.

    Never use assembly matrix ``tok-*`` — identity requires hashed session tokens.
    """
    existing = (
        env.get("VERIFY_IDENTITY_ADMIN_TOKEN") or env.get("VERIFY_IDENTITY_TOKEN") or ""
    ).strip()
    if existing:
        if existing.startswith("tok-"):
            raise AssertionError(
                "VERIFY_IDENTITY_ADMIN_TOKEN looks like matrix tok-*; "
                "use identity login session_token instead"
            )
        return existing
    email = (env.get("VERIFY_IDENTITY_ADMIN_EMAIL") or SEED_ADMIN_EMAIL).strip()
    password = (
        env.get("VERIFY_IDENTITY_ADMIN_PASSWORD")
        or env.get("IDENTITY_DEMO_PASSWORD")
        or DEFAULT_DEMO_PASSWORD
    )
    status, body = _request_json(
        f"{identity_base}/v1/auth/login",
        method="POST",
        payload={
            "email": email,
            "password": password,
            "requested_role": "platform_admin",
        },
    )
    if status != 200 or not isinstance(body, dict):
        raise AssertionError(f"admin login failed status={status} body={body!r}")
    token = body.get("session_token")
    if not isinstance(token, str) or not token.strip():
        raise AssertionError("admin login missing session_token (seed / peers required)")
    if token.startswith("tok-"):
        raise AssertionError("admin login returned matrix-shaped tok-* token; refuse")
    return token


def verify_wave5(env: Mapping[str, str] | None = None) -> VerifyReport:
    """Hit admin peers; require seed / catalog rows. Fails closed without peers.

    Tokens: identity session (login); policy ``tok-platform-admin``; merchant-teams
    ``platform-admin-token``; platform-ai / evals / observability ``admin-token``.
    Documented in sandbox-matrix + README. No real money.
    """
    env = env or {}
    identity_base = (
        env.get("VERIFY_IDENTITY_URL")
        or env.get("CORE_ASSEMBLY_IDENTITY_URL")
        or DEFAULT_IDENTITY_URL
    ).rstrip("/")
    policy_base = (env.get("VERIFY_POLICY_URL") or DEFAULT_POLICY_URL).rstrip("/")
    merchants_base = (env.get("VERIFY_MERCHANT_TEAMS_URL") or DEFAULT_MERCHANT_TEAMS_URL).rstrip(
        "/"
    )
    platform_ai_base = (env.get("VERIFY_PLATFORM_AI_URL") or DEFAULT_PLATFORM_AI_URL).rstrip("/")
    evals_base = (env.get("VERIFY_EVALS_URL") or DEFAULT_EVALS_URL).rstrip("/")
    obs_base = (env.get("VERIFY_OBSERVABILITY_URL") or DEFAULT_OBSERVABILITY_URL).rstrip("/")

    policy_token = env.get("VERIFY_POLICY_TOKEN") or DEFAULT_POLICY_TOKEN
    merchants_token = env.get("VERIFY_MERCHANT_TEAMS_TOKEN") or DEFAULT_MERCHANT_TEAMS_TOKEN
    platform_ai_token = env.get("VERIFY_PLATFORM_AI_TOKEN") or DEFAULT_PLATFORM_AI_TOKEN
    evals_token = env.get("VERIFY_EVALS_TOKEN") or DEFAULT_EVALS_TOKEN
    obs_token = env.get("VERIFY_OBSERVABILITY_TOKEN") or DEFAULT_OBSERVABILITY_TOKEN

    checks: list[CheckResult] = []

    try:
        admin_token = _resolve_admin_session(identity_base, env)
    except Exception as exc:  # noqa: BLE001 — surface connect/login as check failure
        return {
            "status": "FAIL",
            "checks": [
                {
                    "name": "identity.admin.session",
                    "ok": False,
                    "status_code": 0,
                    "detail": f"admin session resolve failed: {exc}",
                }
            ],
            "reason_code": "WAVE5_VERIFY_FAILED",
        }

    checks.append(
        {
            "name": "identity.admin.session",
            "ok": True,
            "status_code": 200,
            "detail": "ok",
        }
    )

    def run(
        name: str,
        url: str,
        assert_body,
        *,
        token: str | None = None,
    ) -> None:
        try:
            status, body = _request_json(url, token=token)
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

    run("identity.health", f"{identity_base}/healthz", assert_health_body)
    run(
        "identity.admin.roles",
        f"{identity_base}/v1/admin/roles",
        assert_roles_body,
        token=admin_token,
    )
    run(
        "identity.admin.tenants",
        f"{identity_base}/v1/admin/tenants",
        assert_tenants_body,
        token=admin_token,
    )
    run("policy.health", f"{policy_base}/healthz", assert_health_body)
    run(
        "policy.policies",
        f"{policy_base}/v1/policies",
        assert_policies_body,
        token=policy_token,
    )
    run("merchant-teams.health", f"{merchants_base}/healthz", assert_health_body)
    run(
        "merchant-teams.admin.merchants",
        f"{merchants_base}/v1/admin/merchants",
        assert_merchants_body,
        token=merchants_token,
    )
    run("platform-ai.health", f"{platform_ai_base}/healthz", assert_health_body)
    run(
        "platform-ai.config",
        f"{platform_ai_base}/v1/config",
        assert_config_body,
        token=platform_ai_token,
    )
    run(
        "platform-ai.integrations",
        f"{platform_ai_base}/v1/integrations",
        assert_integrations_body,
        token=platform_ai_token,
    )
    run("evals.health", f"{evals_base}/healthz", assert_health_body)
    run(
        "evals.reports",
        f"{evals_base}/v1/reports",
        assert_reports_body,
        token=evals_token,
    )
    run("observability.health", f"{obs_base}/healthz", assert_health_body)
    run(
        "observability.signals",
        f"{obs_base}/v1/signals",
        assert_signals_body,
        token=obs_token,
    )

    if all(c.get("ok") for c in checks):
        return {"status": "PASS", "checks": checks}
    return {
        "status": "FAIL",
        "checks": checks,
        "reason_code": "WAVE5_VERIFY_FAILED",
    }
