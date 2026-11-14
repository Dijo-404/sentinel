"""Sandbox-only seed: one OPEN dispute for tenant-demo."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

from ..domain.types import DisputeCase
from .storage_postgres import PostgresDisputeStore, build_engine

SANDBOX_TENANT = "tenant-demo"
SEED_DISPUTE_ID = "dispute-seed-demo-1"
SEED_IDEMPOTENCY = "seed-demo-open-1"


class SeedReport(TypedDict, total=False):
    status: str
    rows: int
    reason_code: str
    dispute_id: str


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def seed_sandbox_dispute(env: Mapping[str, str]) -> SeedReport:
    """Insert one OPEN dispute for tenant-demo. Refuse other tenants / missing sandbox."""
    tenant = (env.get("DISPUTES_TENANT_ID") or SANDBOX_TENANT).strip()
    if tenant != SANDBOX_TENANT:
        return {"status": "FAIL", "rows": 0, "reason_code": "SANDBOX_TENANT_REQUIRED"}
    if not _truthy(env.get("SENTINEL_V1_SANDBOX")) and not _truthy(env.get("DISPUTES_SANDBOX")):
        return {"status": "FAIL", "rows": 0, "reason_code": "SANDBOX_FLAG_REQUIRED"}
    database_url = (env.get("DISPUTES_DATABASE_URL") or "").strip()
    if not database_url.startswith("postgresql"):
        return {"status": "FAIL", "rows": 0, "reason_code": "POSTGRES_URL_REQUIRED"}

    store = PostgresDisputeStore(build_engine(database_url))
    store.migrate()
    existing = store.get(SEED_DISPUTE_ID)
    if existing is not None:
        return {
            "status": "PASS",
            "rows": 1,
            "dispute_id": existing.dispute_id,
        }
    dispute = DisputeCase(
        dispute_id=SEED_DISPUTE_ID,
        tenant_id=SANDBOX_TENANT,
        merchant_ref=env.get("DISPUTES_SEED_MERCHANT_REF", "merchant-demo").strip()
        or "merchant-demo",
        case_id=env.get("DISPUTES_SEED_CASE_ID", "case-demo-42").strip() or "case-demo-42",
        reason_code="CHARGEBACK_DUPLICATE",
        deadline_at="2026-11-20T12:30:00Z",
        evidence_packet_ids=(),
        status="OPEN",
        order_reference="DEMO-ORDER-42",
        case_revision=1,
    )
    stored = store.create(dispute, idempotency_key=SEED_IDEMPOTENCY)
    return {
        "status": "PASS",
        "rows": 1,
        "dispute_id": stored.dispute_id,
    }


def seed_report_as_dict(report: SeedReport) -> dict[str, Any]:
    return dict(report)
