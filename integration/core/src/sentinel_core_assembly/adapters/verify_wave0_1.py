"""Wave 0–1 live peer checks: metrics + dispute list + risk list from seeded DBs."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any, TypedDict

DEFAULT_ANALYTICS_URL = "http://127.0.0.1:8032"
DEFAULT_DISPUTES_URL = "http://127.0.0.1:8030"
DEFAULT_RISK_URL = "http://127.0.0.1:8013"

DEFAULT_ANALYTICS_TOKEN = "operator-token"
DEFAULT_DISPUTES_TOKEN = "operator-token"
DEFAULT_RISK_TOKEN = "tok-risk-officer"

DEFAULT_MERCHANT_METRICS = "merchant-demo-1"
DEFAULT_MERCHANT_DISPUTES = "merchant-demo"
DEFAULT_WINDOW_START = "2026-11-01T00:00:00Z"
DEFAULT_WINDOW_END = "2026-11-14T00:00:00Z"

SEED_DISPUTE_ID = "dispute-seed-demo-1"
SEED_INVESTIGATION_ID = "inv-seed-case-demo-42"


class CheckResult(TypedDict, total=False):
    name: str
    ok: bool
    status_code: int
    detail: str


class VerifyReport(TypedDict, total=False):
    status: str
    checks: list[CheckResult]
    reason_code: str


def assert_metrics_body(body: Any) -> None:
    """Fail unless body looks like a seeded MerchantMetrics row (not empty/error)."""
    if not isinstance(body, dict):
        raise AssertionError("metrics body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"metrics error code={body.get('code')!r}")
    if body.get("merchant_ref") != DEFAULT_MERCHANT_METRICS:
        got = body.get("merchant_ref")
        raise AssertionError(f"metrics merchant_ref want {DEFAULT_MERCHANT_METRICS!r} got {got!r}")
    if "exception_rate" not in body or "unresolved_minor" not in body:
        raise AssertionError("metrics missing exception_rate or unresolved_minor")


def assert_disputes_body(body: Any) -> None:
    """Fail unless at least one seeded dispute is present (empty list = unseeded)."""
    if not isinstance(body, dict):
        raise AssertionError("disputes body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"disputes error code={body.get('code')!r}")
    items = body.get("disputes")
    if not isinstance(items, list) or not items:
        raise AssertionError("disputes list empty or missing (seed required)")
    ids = {row.get("dispute_id") for row in items if isinstance(row, dict)}
    if SEED_DISPUTE_ID not in ids:
        raise AssertionError(f"seed dispute {SEED_DISPUTE_ID!r} not in list {sorted(ids)!r}")


def assert_risk_list_body(body: Any) -> None:
    """Fail unless at least one seeded investigation is present."""
    if not isinstance(body, dict):
        raise AssertionError("risk body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"risk error code={body.get('code')!r}")
    items = body.get("investigations")
    if not isinstance(items, list) or not items:
        raise AssertionError("investigations list empty or missing (seed required)")
    ids = {row.get("investigation_id") for row in items if isinstance(row, dict)}
    if SEED_INVESTIGATION_ID not in ids:
        raise AssertionError(
            f"seed investigation {SEED_INVESTIGATION_ID!r} not in list {sorted(ids)!r}"
        )


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


def verify_wave0_1(env: Mapping[str, str] | None = None) -> VerifyReport:
    """Hit DB-backed peers; require HTTP 200 + seeded JSON. Fails closed without seed."""
    env = env or {}
    analytics_base = (env.get("VERIFY_ANALYTICS_URL") or DEFAULT_ANALYTICS_URL).rstrip("/")
    disputes_base = (env.get("VERIFY_DISPUTES_URL") or DEFAULT_DISPUTES_URL).rstrip("/")
    risk_base = (
        env.get("VERIFY_RISK_URL") or env.get("CORE_ASSEMBLY_RISK_URL") or DEFAULT_RISK_URL
    ).rstrip("/")
    analytics_token = env.get("VERIFY_ANALYTICS_TOKEN") or DEFAULT_ANALYTICS_TOKEN
    disputes_token = env.get("VERIFY_DISPUTES_TOKEN") or DEFAULT_DISPUTES_TOKEN
    risk_token = (
        env.get("VERIFY_RISK_TOKEN")
        or env.get("CORE_ASSEMBLY_TOKEN_RISK_OFFICER")
        or DEFAULT_RISK_TOKEN
    )
    merchant_metrics = env.get("VERIFY_MERCHANT_REF_METRICS") or DEFAULT_MERCHANT_METRICS
    merchant_disputes = env.get("VERIFY_MERCHANT_REF_DISPUTES") or DEFAULT_MERCHANT_DISPUTES
    window_start = env.get("VERIFY_WINDOW_START") or DEFAULT_WINDOW_START
    window_end = env.get("VERIFY_WINDOW_END") or DEFAULT_WINDOW_END

    qs = urllib.parse.urlencode({"window_start": window_start, "window_end": window_end})
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
        "merchant-analytics.metrics",
        f"{analytics_base}/v1/merchants/{merchant_metrics}/metrics?{qs}",
        analytics_token,
        assert_metrics_body,
    )
    run(
        "merchant-disputes.list",
        f"{disputes_base}/v1/merchants/{merchant_disputes}/disputes",
        disputes_token,
        assert_disputes_body,
    )
    run(
        "risk.investigations",
        f"{risk_base}/v1/risk/investigations",
        risk_token,
        assert_risk_list_body,
    )

    if all(c.get("ok") for c in checks):
        return {"status": "PASS", "checks": checks}
    return {
        "status": "FAIL",
        "checks": checks,
        "reason_code": "WAVE0_1_VERIFY_FAILED",
    }
