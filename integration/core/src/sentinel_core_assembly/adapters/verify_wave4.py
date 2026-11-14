"""Wave 4 live peer checks: intel health/list + voice caps + approval-ui smoke."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypedDict

DEFAULT_ASSISTANT_URL = "http://127.0.0.1:8026"
DEFAULT_KNOWLEDGE_URL = "http://127.0.0.1:8035"
DEFAULT_OPS_ACTIVITY_URL = "http://127.0.0.1:8029"
DEFAULT_VOICE_URL = "http://127.0.0.1:8017"

DEFAULT_ASSISTANT_TOKEN = "tok-customer"
DEFAULT_KNOWLEDGE_TOKEN = "operator-token"
DEFAULT_OPS_ACTIVITY_TOKEN = "operator-token"

SEED_THREAD_ID = "thr-seed-tenant-demo"
SEED_ARTICLE_ID = "article-demo-refund-policy"
SEED_ACTIVITY_ID = "act-seed-case-demo-42"

APPROVAL_UI_PACKAGE_NAME = "sentinel-approval-ui"
APPROVAL_UI_EXPORT = "ApprovalPanel"


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


def assert_threads_body(body: Any) -> None:
    """Fail unless seeded assistant thread is present."""
    if not isinstance(body, dict):
        raise AssertionError("threads body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"threads error code={body.get('code')!r}")
    items = body.get("threads")
    if not isinstance(items, list) or not items:
        raise AssertionError("threads list empty or missing (seed required)")
    ids = {row.get("thread_id") for row in items if isinstance(row, dict)}
    if SEED_THREAD_ID not in ids:
        raise AssertionError(f"seed thread {SEED_THREAD_ID!r} not in list {sorted(ids)!r}")


def assert_articles_body(body: Any) -> None:
    """Fail unless seeded knowledge article is present."""
    if not isinstance(body, dict):
        raise AssertionError("articles body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"articles error code={body.get('code')!r}")
    items = body.get("articles")
    if not isinstance(items, list) or not items:
        raise AssertionError("articles list empty or missing (seed required)")
    ids = {row.get("article_id") for row in items if isinstance(row, dict)}
    if SEED_ARTICLE_ID not in ids:
        raise AssertionError(f"seed article {SEED_ARTICLE_ID!r} not in list {sorted(ids)!r}")


def assert_activity_body(body: Any) -> None:
    """Fail unless seeded ops-activity row is present."""
    if not isinstance(body, dict):
        raise AssertionError("activity body must be a JSON object")
    if body.get("code"):
        raise AssertionError(f"activity error code={body.get('code')!r}")
    items = body.get("items")
    if not isinstance(items, list) or not items:
        raise AssertionError("activity items empty or missing (seed required)")
    ids = {row.get("activity_id") for row in items if isinstance(row, dict)}
    if SEED_ACTIVITY_ID not in ids:
        raise AssertionError(f"seed activity {SEED_ACTIVITY_ID!r} not in list {sorted(ids)!r}")


def assert_voice_capabilities_body(body: Any) -> None:
    """Fail unless voice capabilities advertise voice.v1."""
    if not isinstance(body, dict):
        raise AssertionError("voice capabilities body must be a JSON object")
    if body.get("component") != "voice":
        raise AssertionError(f"voice component want 'voice' got {body.get('component')!r}")
    if body.get("port") != "voice.v1":
        raise AssertionError(f"voice port want 'voice.v1' got {body.get('port')!r}")


def assert_approval_ui_package(repo_root: Path) -> None:
    """Fail unless packages/approval-ui exports ApprovalPanel (import smoke, no live UI)."""
    pkg_dir = repo_root / "packages" / "approval-ui"
    package_json = pkg_dir / "package.json"
    index_ts = pkg_dir / "src" / "index.ts"
    if not package_json.is_file():
        raise AssertionError(f"missing {package_json}")
    try:
        meta = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"approval-ui package.json invalid: {exc}") from exc
    if not isinstance(meta, dict) or meta.get("name") != APPROVAL_UI_PACKAGE_NAME:
        raise AssertionError(
            f"approval-ui package name want {APPROVAL_UI_PACKAGE_NAME!r} got {meta.get('name')!r}"
        )
    if not index_ts.is_file():
        raise AssertionError(f"missing {index_ts}")
    text = index_ts.read_text(encoding="utf-8")
    if APPROVAL_UI_EXPORT not in text:
        raise AssertionError(f"{index_ts} missing export {APPROVAL_UI_EXPORT!r}")


def _repo_root() -> Path:
    # adapters → package → src → integration/core → integration → repo
    return Path(__file__).resolve().parents[5]


def _request_json(
    url: str,
    *,
    token: str | None = None,
    timeout: float = 5.0,
) -> tuple[int, Any]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
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


def verify_wave4(
    env: Mapping[str, str] | None = None,
    *,
    repo_root: Path | None = None,
) -> VerifyReport:
    """Hit intel peers + voice; require seed rows. Offline approval-ui package smoke.

    Fails closed without seed / peers down. No real money. Approval-ui smoke is
    filesystem export check (document live: make -C packages/approval-ui check).
    """
    env = env or {}
    root = repo_root or _repo_root()
    assistant_base = (env.get("VERIFY_ASSISTANT_URL") or DEFAULT_ASSISTANT_URL).rstrip("/")
    knowledge_base = (env.get("VERIFY_KNOWLEDGE_URL") or DEFAULT_KNOWLEDGE_URL).rstrip("/")
    activity_base = (env.get("VERIFY_OPS_ACTIVITY_URL") or DEFAULT_OPS_ACTIVITY_URL).rstrip("/")
    voice_base = (env.get("VERIFY_VOICE_URL") or DEFAULT_VOICE_URL).rstrip("/")
    assistant_token = env.get("VERIFY_ASSISTANT_TOKEN") or DEFAULT_ASSISTANT_TOKEN
    knowledge_token = env.get("VERIFY_KNOWLEDGE_TOKEN") or DEFAULT_KNOWLEDGE_TOKEN
    activity_token = env.get("VERIFY_OPS_ACTIVITY_TOKEN") or DEFAULT_OPS_ACTIVITY_TOKEN

    checks: list[CheckResult] = []

    def run(
        name: str,
        url: str,
        assert_body,
        *,
        token: str | None = None,
    ) -> None:
        try:
            status, body = _request_json(url, token=token)
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

    run("assistant.health", f"{assistant_base}/healthz", assert_health_body)
    run(
        "assistant.threads",
        f"{assistant_base}/v1/threads?role=customer",
        assert_threads_body,
        token=assistant_token,
    )
    run("knowledge.health", f"{knowledge_base}/healthz", assert_health_body)
    run(
        "knowledge.articles",
        f"{knowledge_base}/v1/articles",
        assert_articles_body,
        token=knowledge_token,
    )
    run("ops-activity.health", f"{activity_base}/healthz", assert_health_body)
    run(
        "ops-activity.activity",
        f"{activity_base}/v1/activity",
        assert_activity_body,
        token=activity_token,
    )
    run(
        "voice.capabilities",
        f"{voice_base}/v1/capabilities",
        assert_voice_capabilities_body,
    )

    try:
        assert_approval_ui_package(root)
        checks.append(
            {
                "name": "approval-ui.package",
                "ok": True,
                "status_code": 0,
                "detail": "ok",
            }
        )
    except AssertionError as exc:
        checks.append(
            {
                "name": "approval-ui.package",
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
        "reason_code": "WAVE4_VERIFY_FAILED",
    }
