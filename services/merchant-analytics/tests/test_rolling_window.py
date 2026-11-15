"""Seed window must match portal rollingMetricsWindow algorithm."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sentinel_merchant_analytics.domain.metrics_window import rolling_metrics_window


def test_rolling_window_matches_portal_for_nov_15_2026() -> None:
    # Portal probe for 2026-11-15: Nov 2 00:00:00Z → Nov 15 23:59:59Z
    start, end = rolling_metrics_window(
        now=datetime(2026, 11, 15, 10, 17, 0, tzinfo=UTC),
        day_count=14,
    )
    assert start == "2026-11-02T00:00:00Z"
    assert end == "2026-11-15T23:59:59Z"


def test_seed_overrides_fixed_contract_dates(tmp_path, monkeypatch) -> None:
    from sentinel_merchant_analytics import seed as seed_mod

    held: dict = {}

    class _Store:
        def migrate(self) -> None:
            return None

        def put(self, metrics) -> None:
            held["metrics"] = metrics

    monkeypatch.setattr(seed_mod, "build_engine", lambda _url: object())
    monkeypatch.setattr(seed_mod, "PostgresMetricsSnapshotStore", lambda _engine: _Store())

    snapshot = tmp_path / "snap.json"
    snapshot.write_text(
        json.dumps(
            {
                "tenant_id": "tenant-demo",
                "merchant_ref": "merchant-demo-1",
                "window_start": "2026-11-01T00:00:00Z",
                "window_end": "2026-11-14T00:00:00Z",
                "exception_rate": "0.4000",
                "unresolved_minor": 100000,
                "currency": "INR",
                "refund_aging_buckets": {"0-24h": 1},
                "median_handling_seconds": 2700,
                "top_causes": ["DUPLICATE_PAYMENT"],
            }
        ),
        encoding="utf-8",
    )
    metrics = seed_mod.seed_demo_snapshot(
        "postgresql://example/db",
        snapshot_path=snapshot,
        now=datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC),
    )
    assert metrics.window_start == "2026-11-02T00:00:00Z"
    assert metrics.window_end == "2026-11-15T23:59:59Z"
    assert held["metrics"].window_end == "2026-11-15T23:59:59Z"
