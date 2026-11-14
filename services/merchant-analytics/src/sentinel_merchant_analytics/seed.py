"""Sandbox seed: one metrics snapshot for merchant-demo-1 / matrix window."""

from __future__ import annotations

import json
from pathlib import Path

from .adapters.postgres_snapshots import PostgresMetricsSnapshotStore, build_engine
from .application.errors import ConfigurationError
from .domain.types import MerchantMetrics

MODULE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = MODULE_ROOT / "contracts" / "expected-metrics.json"
SANDBOX_TENANT = "tenant-demo"
SANDBOX_MERCHANT = "merchant-demo-1"


def seed_demo_snapshot(database_url: str, *, snapshot_path: Path | None = None) -> MerchantMetrics:
    if not database_url.strip():
        raise ConfigurationError("MERCHANT_ANALYTICS_DATABASE_URL is required for seed")
    path = snapshot_path or DEFAULT_SNAPSHOT
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("tenant_id") != SANDBOX_TENANT:
        raise ConfigurationError(f"seed refuses tenant_id != {SANDBOX_TENANT}")
    if payload.get("merchant_ref") != SANDBOX_MERCHANT:
        raise ConfigurationError(f"seed refuses merchant_ref != {SANDBOX_MERCHANT}")
    metrics = MerchantMetrics(
        tenant_id=payload["tenant_id"],
        merchant_ref=payload["merchant_ref"],
        window_start=payload["window_start"],
        window_end=payload["window_end"],
        exception_rate=payload["exception_rate"],
        unresolved_minor=int(payload["unresolved_minor"]),
        currency=payload["currency"],
        refund_aging_buckets={
            str(k): int(v) for k, v in dict(payload["refund_aging_buckets"]).items()
        },
        median_handling_seconds=int(payload["median_handling_seconds"]),
        top_causes=tuple(str(c) for c in list(payload["top_causes"])),
    )
    store = PostgresMetricsSnapshotStore(build_engine(database_url))
    store.migrate()
    store.put(metrics)
    return metrics
