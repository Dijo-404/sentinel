"""Sandbox seed: one synthetic span signal for tenant-demo."""

from __future__ import annotations

from typing import Any

from .adapters.postgres_store import PostgresSignalStore, build_engine
from .application.errors import ConfigurationError
from .domain.types import Signal

SEED_TENANT_ID = "tenant-demo"
SEED_SIGNAL_ID = "sig-seed-request-handle"
SEED_SIGNAL_NAME = "request.handle"
SEED_RECORDED_AT = "2026-11-14T10:00:00Z"
SEED_ATTRIBUTES = {
    "request_id": "req-seed-demo",
    "case_id": "case-demo-42",
}
SEED_EVENTS = [{"name": "accepted", "attributes": {"event.kind": "accepted"}}]


def seed_demo_signal(database_url: str) -> dict[str, Any]:
    """Write synthetic span for portal real-peers. Requires OBSERVABILITY_DATABASE_URL."""
    if not database_url.strip():
        raise ConfigurationError("OBSERVABILITY_DATABASE_URL is required for seed")

    item = Signal(
        signal_id=SEED_SIGNAL_ID,
        tenant_id=SEED_TENANT_ID,
        kind="span",
        name=SEED_SIGNAL_NAME,
        attributes=dict(SEED_ATTRIBUTES),
        events=list(SEED_EVENTS),
        recorded_at=SEED_RECORDED_AT,
    )
    if item.tenant_id != SEED_TENANT_ID:
        raise ConfigurationError(f"seed refuses tenant_id != {SEED_TENANT_ID}")

    store = PostgresSignalStore(build_engine(database_url))
    store.migrate()
    store.put(item)
    return {
        "status": "PASS",
        "peer": "observability",
        "tenant_id": SEED_TENANT_ID,
        "signal_id": SEED_SIGNAL_ID,
        "name": SEED_SIGNAL_NAME,
        "rows": 1,
        "financial_audit": False,
        "evidence_label": "synthetic-sandbox",
        "note": "Sampled telemetry only; never financial audit",
    }
