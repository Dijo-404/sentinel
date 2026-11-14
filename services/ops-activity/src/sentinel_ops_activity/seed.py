"""Sandbox seed: one activity row for tenant-demo / case-demo-42."""

from __future__ import annotations

from typing import Any

from .adapters.postgres_store import PostgresActivityStore, build_engine
from .application.errors import ConfigurationError
from .domain.types import ActivityItem

SEED_TENANT_ID = "tenant-demo"
SEED_CASE_ID = "case-demo-42"
SEED_ACTIVITY_ID = "act-seed-case-demo-42"
SEED_KIND = "case.opened"
SEED_SUMMARY = "Sandbox case case-demo-42 opened"
SEED_OCCURRED_AT = "2026-11-14T10:00:00Z"


def seed_demo_activity(database_url: str) -> dict[str, Any]:
    """Write synthetic activity for portal real-peers. Requires OPS_ACTIVITY_DATABASE_URL."""
    if not database_url.strip():
        raise ConfigurationError("OPS_ACTIVITY_DATABASE_URL is required for seed")

    item = ActivityItem(
        activity_id=SEED_ACTIVITY_ID,
        tenant_id=SEED_TENANT_ID,
        kind=SEED_KIND,
        summary=SEED_SUMMARY,
        occurred_at=SEED_OCCURRED_AT,
        case_id=SEED_CASE_ID,
    )
    if item.tenant_id != SEED_TENANT_ID:
        raise ConfigurationError(f"seed refuses tenant_id != {SEED_TENANT_ID}")

    store = PostgresActivityStore(build_engine(database_url))
    store.migrate()
    store.put(item)
    return {
        "status": "PASS",
        "peer": "ops-activity",
        "tenant_id": SEED_TENANT_ID,
        "activity_id": SEED_ACTIVITY_ID,
        "case_id": SEED_CASE_ID,
        "rows": 1,
        "evidence_label": "synthetic-sandbox",
        "projection": "local-seed-only",
        "note": "case-api event projection not wired; sync stub is local seed rows only",
    }
