"""Sandbox-only seed: ops escalations / messages / history / audit for tenant-demo."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

from sqlalchemy import create_engine

from sentinel_api.adapters.db.repository import SqlCaseRepository
from sentinel_api.adapters.db.schema import metadata
from sentinel_api.domain.types import CaseCreate, CaseResult, Principal

SANDBOX_TENANT = "tenant-demo"
SEED_TENANT_ID = SANDBOX_TENANT
SEED_ESCALATED_CASE_ID = "case-seed-ops-escalated"
SEED_HISTORY_CASE_ID = "case-seed-ops-history"
SEED_SUBJECT = "subject-a"
SEED_ORDER = "subject-a/DEMO-ORDER-42"
SEED_OCCURRED_AT = "2026-11-15T10:00:00Z"
SEED_LANGUAGE = "en-IN"
SEED_CHANNEL = "web"


class SeedReport(TypedDict, total=False):
    status: str
    rows: int
    reason_code: str
    tenant_id: str
    case_ids: list[str]
    evidence_label: str


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _customer() -> Principal:
    return Principal(
        principal_id="customer-seed-demo",
        tenant_id=SANDBOX_TENANT,
        roles=("customer",),
        subject_refs=(SEED_SUBJECT,),
    )


def _operator() -> Principal:
    return Principal(
        principal_id="operator-seed-demo",
        tenant_id=SANDBOX_TENANT,
        roles=("operator",),
    )


def _workflow() -> Principal:
    return Principal(
        principal_id="workflow-seed-demo",
        tenant_id=SANDBOX_TENANT,
        roles=("workflow",),
        case_ids=("*",),
    )


def _ensure_escalated(repo: SqlCaseRepository) -> None:
    meta = repo.get_case_meta(tenant_id=SANDBOX_TENANT, case_id=SEED_ESCALATED_CASE_ID)
    if meta is not None and meta["status"] == "ESCALATED":
        return
    customer = _customer()
    if meta is None:
        create = CaseCreate(
            message="Sandbox ops seed: escalated duplicate charge",
            language=SEED_LANGUAGE,
            order_reference=SEED_ORDER,
            channel=SEED_CHANNEL,  # type: ignore[arg-type]
        )
        repo.create_case(
            principal=customer,
            create=create,
            idempotency_key="seed-ops-escalated-1",
            case_id=SEED_ESCALATED_CASE_ID,
            message_id="msg-seed-ops-escalated-1",
            event_id="evt-seed-ops-escalated-created",
            occurred_at=SEED_OCCURRED_AT,
        )
        meta = repo.get_case_meta(tenant_id=SANDBOX_TENANT, case_id=SEED_ESCALATED_CASE_ID)
        assert meta is not None
    if meta["status"] == "ESCALATED":
        return
    repo.escalate(
        principal=_operator(),
        case_id=SEED_ESCALATED_CASE_ID,
        expected_revision=int(meta["revision"]),
        reason_code="SANDBOX_SEED_ESCALATE",
        owner_queue="SUPERVISOR",
        event_id="evt-seed-ops-escalated",
        occurred_at=SEED_OCCURRED_AT,
    )


def _ensure_history(repo: SqlCaseRepository) -> None:
    meta = repo.get_case_meta(tenant_id=SANDBOX_TENANT, case_id=SEED_HISTORY_CASE_ID)
    if meta is not None and meta["status"] in {"VERIFIED_RESOLVED", "CLOSED_NO_ACTION"}:
        return
    customer = _customer()
    if meta is None:
        create = CaseCreate(
            message="Sandbox ops seed: closed history case",
            language=SEED_LANGUAGE,
            order_reference=SEED_ORDER,
            channel=SEED_CHANNEL,  # type: ignore[arg-type]
        )
        repo.create_case(
            principal=customer,
            create=create,
            idempotency_key="seed-ops-history-1",
            case_id=SEED_HISTORY_CASE_ID,
            message_id="msg-seed-ops-history-1",
            event_id="evt-seed-ops-history-created",
            occurred_at=SEED_OCCURRED_AT,
        )
        meta = repo.get_case_meta(tenant_id=SANDBOX_TENANT, case_id=SEED_HISTORY_CASE_ID)
        assert meta is not None
    if meta["status"] in {"VERIFIED_RESOLVED", "CLOSED_NO_ACTION"}:
        return
    result = CaseResult(
        event_key="seed-ops-history-close-1",
        expected_revision=int(meta["revision"]),
        status="CLOSED_NO_ACTION",
        evidence_ids=(),
        reason_code="NO_ACTION",
    )
    repo.apply_result(
        principal=_workflow(),
        case_id=SEED_HISTORY_CASE_ID,
        result=result,
        event_id="evt-seed-ops-history-closed",
        occurred_at=SEED_OCCURRED_AT,
        assessment_ref=None,
    )


def seed_ops_surfaces(env: Mapping[str, str]) -> SeedReport:
    """Insert ESCALATED + HISTORY cases (messages + audit events) for tenant-demo."""
    tenant = (
        env.get("CORE_ASSEMBLY_TENANT_ID") or env.get("SENTINEL_API_TENANT_ID") or SANDBOX_TENANT
    ).strip()
    if tenant != SANDBOX_TENANT:
        return {"status": "FAIL", "rows": 0, "reason_code": "SANDBOX_TENANT_REQUIRED"}
    if not _truthy(env.get("SENTINEL_V1_SANDBOX")) and not _truthy(env.get("SENTINEL_API_SANDBOX")):
        return {"status": "FAIL", "rows": 0, "reason_code": "SANDBOX_FLAG_REQUIRED"}
    database_url = (env.get("SENTINEL_API_DATABASE_URL") or "").strip()
    if not database_url.startswith("postgresql"):
        return {"status": "FAIL", "rows": 0, "reason_code": "POSTGRES_URL_REQUIRED"}

    engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True)
    try:
        metadata.create_all(engine)
        repo = SqlCaseRepository(engine)
        _ensure_escalated(repo)
        _ensure_history(repo)
    finally:
        engine.dispose()

    return {
        "status": "PASS",
        "rows": 2,
        "tenant_id": SANDBOX_TENANT,
        "case_ids": [SEED_ESCALATED_CASE_ID, SEED_HISTORY_CASE_ID],
        "evidence_label": "synthetic-sandbox",
    }


def seed_report_as_dict(report: SeedReport) -> dict[str, Any]:
    return dict(report)
