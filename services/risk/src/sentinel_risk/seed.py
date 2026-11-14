"""Sandbox seed: investigation + restriction + finding for case-demo-42."""

from __future__ import annotations

from typing import Any

from .adapters.storage_postgres import PostgresRiskStore, build_engine
from .application.errors import ConfigurationError
from .application.risk import POLICY_VERSION
from .domain.types import Finding, Investigation, RiskRestriction

SEED_TENANT_ID = "tenant-demo"
SEED_CASE_ID = "case-demo-42"
SEED_INVESTIGATION_ID = "inv-seed-case-demo-42"
SEED_RESTRICTION_ID = "rst-seed-case-demo-42"
SEED_FINDING_ID = "fnd-seed-case-demo-42"
SEED_TRANSACTION_REF = "TXN-B"
SEED_OWNER = "risk-officer-demo"
SEED_CREATED_AT = "2026-11-14T10:00:00Z"
SEED_REVIEW_DUE_AT = "2026-11-21T10:00:00Z"


def seed_demo_case(database_url: str) -> dict[str, Any]:
    """Write synthetic risk rows for portal real-peers. Requires RISK_DATABASE_URL."""
    if not database_url.strip():
        raise ConfigurationError("RISK_DATABASE_URL is required for seed")

    investigation = Investigation(
        investigation_id=SEED_INVESTIGATION_ID,
        tenant_id=SEED_TENANT_ID,
        case_id=SEED_CASE_ID,
        case_revision=1,
        reason_code="SUSPECTED_DUPLICATE",
        status="OPEN",
        queue_ref="FRAUD",
        owner_principal_id=SEED_OWNER,
        severity="HIGH",
        created_at=SEED_CREATED_AT,
        updated_at=SEED_CREATED_AT,
        revision=2,
        finding_ids=(SEED_FINDING_ID,),
        restriction_ids=(SEED_RESTRICTION_ID,),
        evidence_ids=("evidence-payment-b", "evidence-order"),
    )
    restriction = RiskRestriction(
        restriction_id=SEED_RESTRICTION_ID,
        tenant_id=SEED_TENANT_ID,
        case_id=SEED_CASE_ID,
        investigation_id=SEED_INVESTIGATION_ID,
        reason_code="SUSPECTED_DUPLICATE",
        status="ACTIVE",
        blocks_financial_actions=True,
        created_at=SEED_CREATED_AT,
        review_due_at=SEED_REVIEW_DUE_AT,
        created_by=SEED_OWNER,
        policy_version=POLICY_VERSION,
        evidence_ids=("evidence-payment-b", "evidence-order"),
        revision=1,
        transaction_ref=SEED_TRANSACTION_REF,
        financial_approval_granted=False,
    )
    finding = Finding(
        finding_id=SEED_FINDING_ID,
        investigation_id=SEED_INVESTIGATION_ID,
        classification="SUSPICIOUS",
        evidence_ids=("evidence-payment-b",),
        notes="Synthetic sandbox finding for portal wave 0-1",
        recorded_by=SEED_OWNER,
        recorded_at=SEED_CREATED_AT,
        revision=2,
    )

    store = PostgresRiskStore(build_engine(database_url))
    store.migrate()
    store.upsert_seed_bundle(investigation, restriction, finding)
    return {
        "status": "PASS",
        "peer": "risk",
        "tenant_id": SEED_TENANT_ID,
        "case_id": SEED_CASE_ID,
        "investigation_id": SEED_INVESTIGATION_ID,
        "restriction_id": SEED_RESTRICTION_ID,
        "finding_ids": [SEED_FINDING_ID],
        "rows": 3,
        "evidence_label": "synthetic-sandbox",
    }
