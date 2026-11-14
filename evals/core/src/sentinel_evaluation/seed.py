"""Sandbox seed: one synthetic evaluation.v1 RunReport for portal/HTTP reads."""

from __future__ import annotations

from typing import Any

from sentinel_evaluation.adapters.storage_postgres import PostgresReportStore, build_engine
from sentinel_evaluation.application.errors import ConfigurationError
from sentinel_evaluation.domain.models import CONTRACT_VERSION

SEED_RUN_ID = "eval-sandbox-1"


def seed_report_wire() -> dict[str, Any]:
    """Wire RunReport matching contracts/evaluation.v1.run-report.pass.example.json."""
    return {
        "contract_version": CONTRACT_VERSION,
        "run_id": SEED_RUN_ID,
        "mode": "fixture",
        "status": "PASS",
        "checks": [
            {
                "name": "critical_safety",
                "status": "PASS",
                "reason_code": "SAFETY_CLEAN",
            }
        ],
        "output_artifacts": [
            {
                "kind": "evaluation.detail.v1",
                "uri": f"memory://evaluation/{SEED_RUN_ID}",
                "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "component_version": "0.1.0",
                "evidence_mode": "fixture",
            }
        ],
    }


def seed_demo_report(database_url: str) -> dict[str, Any]:
    """Write one synthetic RunReport into Postgres. Requires EVALUATION_DATABASE_URL."""
    if not (database_url or "").strip():
        raise ConfigurationError("EVALUATION_DATABASE_URL is required for seed")

    engine = build_engine(database_url)
    try:
        store = PostgresReportStore(engine)
        store.migrate()
        report = seed_report_wire()
        store.put_report(report)
        loaded = store.get_report(SEED_RUN_ID)
        if loaded is None or loaded.get("run_id") != SEED_RUN_ID:
            raise ConfigurationError(f"seed missing RunReport {SEED_RUN_ID!r}")
    finally:
        engine.dispose()

    return {
        "status": "PASS",
        "peer": "evaluation",
        "run_id": SEED_RUN_ID,
        "rows": 1,
        "evidence_label": "synthetic-sandbox",
    }
