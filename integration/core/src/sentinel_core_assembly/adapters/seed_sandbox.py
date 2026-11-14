"""Sandbox-only seed orchestrator. Refuses non-demo tenants; peers may SKIP until migrated."""

from __future__ import annotations

from collections.abc import Mapping
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


# Peers that later waves will hook; Wave 0 documents SKIP until their make seed exists.
_PENDING_PEER_SEEDS: tuple[str, ...] = (
    "case-api",
    "merchant-analytics",
    "merchant-disputes",
    "merchant-teams",
    "merchant-inbox",
    "risk",
    "identity",
    "action-ledger",
    "workflow",
)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def seed_sandbox(env: Mapping[str, str]) -> SeedReport:
    """Seed sandbox DBs for assembly peers.

    Gate: CORE_ASSEMBLY_TENANT_ID must be tenant-demo and SENTINEL_V1_SANDBOX must be truthy.
    Until peer seed hooks land, returns PASS with SKIPPED entries (documented no-ops).
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

    seeds: list[SeedEntry] = [
        {
            "peer": peer,
            "rows": 0,
            "status": "SKIPPED",
            "detail": "peer seed hook not registered yet; wave tasks add make seed",
        }
        for peer in _PENDING_PEER_SEEDS
    ]
    return {"status": "PASS", "seeds": seeds}


def seed_report_as_dict(report: SeedReport) -> dict[str, Any]:
    return dict(report)
