"""Wave 2 live peer checks: case-api ops surfaces (+ optional identity team)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any, TypedDict

DEFAULT_CASE_API_URL = "http://127.0.0.1:8080"
DEFAULT_IDENTITY_URL = "http://127.0.0.1:8012"

# apps/api fixtures/auth_tokens.json (not assembly matrix tok-operator).
DEFAULT_OPERATOR_TOKEN = "token-operator"
DEFAULT_SUPERVISOR_TOKEN = "token-supervisor"

SEED_ESCALATED_CASE_ID = "case-seed-ops-escalated"
SEED_HISTORY_CASE_ID = "case-seed-ops-history"
HISTORY_STATUSES = frozenset({"VERIFIED_RESOLVED", "CLOSED_NO_ACTION"})


class CheckResult(TypedDict, total=False):
    name: str
    ok: bool
    status_code: int
    detail: str


class VerifyReport(TypedDict, total=False):
    status: str
    checks: list[CheckResult]
    reason_code: str


def assert_escalated_body(body: Any) -> None:
    """Fail unless seeded ESCALATED case is present (empty list = unseeded)."""
    if not isinstance(body, dict):
        raise AssertionError("escalated body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"escalated error code={body.get('code')!r}")
    items = body.get("cases")
    if not isinstance(items, list) or not items:
        raise AssertionError("ESCALATED cases list empty or missing (seed required)")
    ids = {row.get("case_id") for row in items if isinstance(row, dict)}
    if SEED_ESCALATED_CASE_ID not in ids:
        raise AssertionError(
            f"seed case {SEED_ESCALATED_CASE_ID!r} not in ESCALATED list {sorted(ids)!r}"
        )


def assert_history_body(body: Any) -> None:
    """Fail unless seeded HISTORY case is present with a terminal status."""
    if not isinstance(body, dict):
        raise AssertionError("history body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"history error code={body.get('code')!r}")
    items = body.get("cases")
    if not isinstance(items, list) or not items:
        raise AssertionError("HISTORY cases list empty or missing (seed required)")
    by_id = {row.get("case_id"): row.get("status") for row in items if isinstance(row, dict)}
    status = by_id.get(SEED_HISTORY_CASE_ID)
    if status not in HISTORY_STATUSES:
        raise AssertionError(
            f"seed case {SEED_HISTORY_CASE_ID!r} want status in "
            f"{sorted(HISTORY_STATUSES)!r} got {status!r} (ids={sorted(by_id)!r})"
        )


def assert_messages_body(body: Any) -> None:
    """Fail unless at least one seeded ops message is present."""
    if not isinstance(body, dict):
        raise AssertionError("messages body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"messages error code={body.get('code')!r}")
    items = body.get("messages")
    if not isinstance(items, list) or not items:
        raise AssertionError("messages list empty or missing (seed required)")
    case_ids = {row.get("case_id") for row in items if isinstance(row, dict)}
    if SEED_ESCALATED_CASE_ID not in case_ids and SEED_HISTORY_CASE_ID not in case_ids:
        raise AssertionError(
            f"seed message case ids missing; got {sorted(case_ids)!r} "
            f"(want {SEED_ESCALATED_CASE_ID!r} or {SEED_HISTORY_CASE_ID!r})"
        )


def assert_audit_events_body(body: Any) -> None:
    """Fail unless at least one seeded ops audit event is present."""
    if not isinstance(body, dict):
        raise AssertionError("audit-events body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"audit-events error code={body.get('code')!r}")
    items = body.get("events")
    if not isinstance(items, list) or not items:
        raise AssertionError("audit-events list empty or missing (seed required)")
    case_ids = {row.get("case_id") for row in items if isinstance(row, dict)}
    if SEED_ESCALATED_CASE_ID not in case_ids and SEED_HISTORY_CASE_ID not in case_ids:
        raise AssertionError(
            f"seed audit case ids missing; got {sorted(case_ids)!r} "
            f"(want {SEED_ESCALATED_CASE_ID!r} or {SEED_HISTORY_CASE_ID!r})"
        )


def assert_ops_team_body(body: Any) -> None:
    """Fail unless identity ops team returns a non-empty members list."""
    if not isinstance(body, dict):
        raise AssertionError("ops team body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"ops team error code={body.get('code')!r}")
    members = body.get("members")
    if not isinstance(members, list) or not members:
        raise AssertionError("ops team members empty or missing")


def _get_json(url: str, token: str, timeout: float = 5.0) -> tuple[int, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            status = getattr(resp, "status", 200)
            return int(status), json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        try:
            payload: Any = json.loads(raw) if raw else {"message": str(exc)}
        except json.JSONDecodeError:
            payload = {"message": raw or str(exc)}
        return int(exc.code), payload


def verify_wave2(env: Mapping[str, str] | None = None) -> VerifyReport:
    """Hit case-api ops surfaces; require HTTP 200 + seeded JSON. Fails closed without seed.

    Identity ``GET /v1/ops/team`` runs only when ``VERIFY_IDENTITY_TOKEN`` (session) is set.
    """
    env = env or {}
    case_base = (
        env.get("VERIFY_CASE_API_URL")
        or env.get("CORE_ASSEMBLY_CASE_API_URL")
        or DEFAULT_CASE_API_URL
    ).rstrip("/")
    identity_base = (
        env.get("VERIFY_IDENTITY_URL")
        or env.get("CORE_ASSEMBLY_IDENTITY_URL")
        or DEFAULT_IDENTITY_URL
    ).rstrip("/")
    # Prefer VERIFY_*; do not fall back to CORE_ASSEMBLY_TOKEN_OPERATOR (matrix
    # tok-operator) — case-api fixture map uses token-operator / token-supervisor.
    operator_token = env.get("VERIFY_OPERATOR_TOKEN") or DEFAULT_OPERATOR_TOKEN
    supervisor_token = env.get("VERIFY_SUPERVISOR_TOKEN") or DEFAULT_SUPERVISOR_TOKEN
    identity_token = (env.get("VERIFY_IDENTITY_TOKEN") or "").strip()

    checks: list[CheckResult] = []

    def run(
        name: str,
        url: str,
        token: str,
        assert_body,
    ) -> None:
        try:
            status, body = _get_json(url, token)
        except Exception as exc:  # noqa: BLE001 — surface connect/DNS as check failure
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

    run(
        "case-api.ops.escalated",
        f"{case_base}/v1/ops/cases?status=ESCALATED",
        operator_token,
        assert_escalated_body,
    )
    run(
        "case-api.ops.history",
        f"{case_base}/v1/ops/cases?status=HISTORY",
        supervisor_token,
        assert_history_body,
    )
    run(
        "case-api.ops.messages",
        f"{case_base}/v1/ops/messages",
        operator_token,
        assert_messages_body,
    )
    run(
        "case-api.ops.audit-events",
        f"{case_base}/v1/ops/audit-events",
        supervisor_token,
        assert_audit_events_body,
    )

    if identity_token:
        run(
            "identity.ops.team",
            f"{identity_base}/v1/ops/team",
            identity_token,
            assert_ops_team_body,
        )
    else:
        checks.append(
            {
                "name": "identity.ops.team",
                "ok": True,
                "status_code": 0,
                "detail": "skipped: VERIFY_IDENTITY_TOKEN unset",
            }
        )

    if all(c.get("ok") for c in checks):
        return {"status": "PASS", "checks": checks}
    return {
        "status": "FAIL",
        "checks": checks,
        "reason_code": "WAVE2_VERIFY_FAILED",
    }
