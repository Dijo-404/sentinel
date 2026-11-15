"""Sandbox-only seed orchestrator. Refuses non-demo tenants; peers may SKIP until migrated."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TypedDict


class SeedEntry(TypedDict):
    peer: str
    rows: int
    status: str
    detail: str


class SeedReport(TypedDict, total=False):
    status: str
    seeds: list[SeedEntry]
    reason_code: str


# Peers without a make-seed hook yet stay documented SKIPPED.
_PENDING_PEER_SEEDS: tuple[str, ...] = (
    "merchant-inbox",
    "action-ledger",
    "workflow",
)

# Wave 0–1 / wave 2 / wave 3 peers: invoke module `make seed` when DATABASE_URL env is present.
_PEER_MAKE_SEEDS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "merchant-analytics",
        "services/merchant-analytics",
        ("MERCHANT_ANALYTICS_DATABASE_URL",),
    ),
    (
        "merchant-disputes",
        "services/merchant-disputes",
        ("DISPUTES_DATABASE_URL",),
    ),
    (
        "risk",
        "services/risk",
        ("RISK_DATABASE_URL",),
    ),
    (
        "case-api",
        "apps/api",
        ("SENTINEL_API_DATABASE_URL",),
    ),
    (
        "identity",
        "services/identity",
        ("IDENTITY_DATABASE_URL",),
    ),
    (
        "assistant",
        "services/assistant",
        ("ASSISTANT_DATABASE_URL",),
    ),
    (
        "knowledge",
        "services/knowledge",
        ("KNOWLEDGE_DATABASE_URL",),
    ),
    (
        "ops-activity",
        "services/ops-activity",
        ("OPS_ACTIVITY_DATABASE_URL",),
    ),
    (
        "platform-ai",
        "services/platform-ai",
        ("PLATFORM_AI_DATABASE_URL",),
    ),
    (
        "evals",
        "evals/core",
        ("EVALUATION_DATABASE_URL",),
    ),
    (
        "observability",
        "services/observability",
        ("OBSERVABILITY_DATABASE_URL",),
    ),
    (
        "merchant-teams",
        "services/merchant-teams",
        ("MERCHANT_TEAMS_DATABASE_URL",),
    ),
)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _repo_root() -> Path:
    # adapters → package → src → integration/core → integration → repo
    return Path(__file__).resolve().parents[5]


def _rows_from_seed_stdout(stdout: str) -> int:
    text = (stdout or "").strip()
    if not text:
        return 0
    # Last JSON object line wins (make may print other noise).
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows = payload.get("rows")
            if isinstance(rows, int):
                return rows
            if payload.get("status") == "PASS":
                return 1
    return 1


def _invoke_make_seed(
    peer: str,
    rel_dir: str,
    env: Mapping[str, str],
    *,
    repo_root: Path | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> SeedEntry:
    root = repo_root or _repo_root()
    target = root / rel_dir
    if not target.is_dir():
        return {
            "peer": peer,
            "rows": 0,
            "status": "SKIPPED",
            "detail": f"module path missing: {rel_dir}",
        }
    run = runner or subprocess.run
    child_env = {**os.environ, **dict(env)}
    child_env.setdefault("SENTINEL_V1_SANDBOX", "1")
    child_env.setdefault("CORE_ASSEMBLY_TENANT_ID", "tenant-demo")
    try:
        completed = run(
            ["make", "-C", str(target), "seed"],
            capture_output=True,
            text=True,
            env=child_env,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "peer": peer,
            "rows": 0,
            "status": "FAIL",
            "detail": f"make seed invoke error: {exc}",
        }
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        return {
            "peer": peer,
            "rows": 0,
            "status": "FAIL",
            "detail": f"make seed exit {completed.returncode}: {err[:500]}",
        }
    rows = _rows_from_seed_stdout(completed.stdout or "")
    return {
        "peer": peer,
        "rows": rows,
        "status": "PASS",
        "detail": "make seed ok",
    }


def seed_sandbox(
    env: Mapping[str, str],
    *,
    repo_root: Path | None = None,
    invoke_peer_seed: Callable[..., SeedEntry] | None = None,
) -> SeedReport:
    """Seed sandbox DBs for assembly peers.

    Gate: CORE_ASSEMBLY_TENANT_ID must be tenant-demo and SENTINEL_V1_SANDBOX must be truthy.
    Peers (merchant-analytics, merchant-disputes, risk, case-api, identity, assistant,
    knowledge, ops-activity, platform-ai, evals, observability, merchant-teams) run
    `make seed` when their DATABASE_URL env var is set; otherwise SKIPPED with run-order
    docs. Other peers SKIP.
    """
    tenant = (env.get("CORE_ASSEMBLY_TENANT_ID") or "tenant-demo").strip()
    if tenant != "tenant-demo":
        return {
            "status": "FAIL",
            "seeds": [],
            "reason_code": "SANDBOX_TENANT_REQUIRED",
        }
    if not _truthy(env.get("SENTINEL_V1_SANDBOX")):
        return {
            "status": "FAIL",
            "seeds": [],
            "reason_code": "SANDBOX_FLAG_REQUIRED",
        }

    invoker = invoke_peer_seed or _invoke_make_seed
    seeds: list[SeedEntry] = []

    for peer, rel_dir, required_keys in _PEER_MAKE_SEEDS:
        missing = [key for key in required_keys if not (env.get(key) or "").strip()]
        if missing:
            seeds.append(
                {
                    "peer": peer,
                    "rows": 0,
                    "status": "SKIPPED",
                    "detail": (f"set {', '.join(missing)} then re-run; or: make -C {rel_dir} seed"),
                }
            )
            continue
        seeds.append(invoker(peer, rel_dir, env, repo_root=repo_root))

    for peer in _PENDING_PEER_SEEDS:
        seeds.append(
            {
                "peer": peer,
                "rows": 0,
                "status": "SKIPPED",
                "detail": "peer seed hook not registered yet; wave tasks add make seed",
            }
        )

    if any(entry["status"] == "FAIL" for entry in seeds):
        return {"status": "FAIL", "seeds": seeds, "reason_code": "PEER_SEED_FAILED"}
    return {"status": "PASS", "seeds": seeds}


def seed_report_as_dict(report: SeedReport) -> dict[str, Any]:
    return dict(report)
