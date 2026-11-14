"""Optional PostgreSQL risk persistence. Used only when RISK_DATABASE_URL is set."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from ..application.errors import ConfigurationError, ConflictError
from ..domain.types import Finding, Investigation, RiskRestriction


def risk_tables(schema: str) -> tuple[Table, Table, Table]:
    metadata = MetaData()
    investigations = Table(
        "risk_investigations",
        metadata,
        Column("investigation_id", String(128), primary_key=True),
        Column("tenant_id", String(256), nullable=False),
        Column("case_id", String(256), nullable=False),
        Column("case_revision", Integer, nullable=False),
        Column("reason_code", String(128), nullable=False),
        Column("status", String(64), nullable=False),
        Column("queue_ref", String(128), nullable=False),
        Column("owner_principal_id", String(256), nullable=True),
        Column("severity", String(64), nullable=False),
        Column("created_at", String(64), nullable=False),
        Column("updated_at", String(64), nullable=False),
        Column("revision", Integer, nullable=False),
        Column("finding_ids", JSONB, nullable=False),
        Column("restriction_ids", JSONB, nullable=False),
        Column("evidence_ids", JSONB, nullable=False),
        schema=schema,
    )
    findings = Table(
        "risk_findings",
        metadata,
        Column("finding_id", String(128), primary_key=True),
        Column("investigation_id", String(128), nullable=False),
        Column("classification", String(64), nullable=False),
        Column("evidence_ids", JSONB, nullable=False),
        Column("notes", Text, nullable=False),
        Column("recorded_by", String(256), nullable=False),
        Column("recorded_at", String(64), nullable=False),
        Column("revision", Integer, nullable=False),
        schema=schema,
    )
    restrictions = Table(
        "risk_restrictions",
        metadata,
        Column("restriction_id", String(128), primary_key=True),
        Column("tenant_id", String(256), nullable=False),
        Column("case_id", String(256), nullable=False),
        Column("investigation_id", String(128), nullable=False),
        Column("reason_code", String(128), nullable=False),
        Column("status", String(64), nullable=False),
        Column("blocks_financial_actions", Boolean, nullable=False),
        Column("created_at", String(64), nullable=False),
        Column("review_due_at", String(64), nullable=False),
        Column("created_by", String(256), nullable=False),
        Column("policy_version", String(128), nullable=False),
        Column("evidence_ids", JSONB, nullable=False),
        Column("revision", Integer, nullable=False),
        Column("transaction_ref", String(256), nullable=True),
        Column("action_id", String(256), nullable=True),
        Column("cleared_by", String(256), nullable=True),
        Column("clearance_reason", Text, nullable=True),
        # Column exists for audit clarity; writes with True are rejected in save.
        Column("financial_approval_granted", Boolean, nullable=False),
        schema=schema,
    )
    return investigations, findings, restrictions


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("A real PostgreSQL connection is required")
    return engine


class PostgresRiskStore:
    def __init__(self, engine: Engine, schema: str = "risk"):
        if engine.dialect.name != "postgresql":
            raise ConfigurationError("A real PostgreSQL connection is required")
        self._engine = engine
        self._schema = schema
        self._investigations, self._findings, self._restrictions = risk_tables(schema)
        self._by_idempotency: dict[str, str] = {}
        self._idempotency_payload: dict[str, str] = {}

    def migrate(self) -> None:
        with self._engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"'))
            self._investigations.create(connection, checkfirst=True)
            self._findings.create(connection, checkfirst=True)
            self._restrictions.create(connection, checkfirst=True)

    def create_investigation(
        self,
        investigation: Investigation,
        restriction: RiskRestriction,
        *,
        idempotency_key: str | None,
    ) -> Investigation:
        if idempotency_key:
            fingerprint = _inv_fingerprint(investigation)
            existing_id = self._by_idempotency.get(idempotency_key)
            if existing_id is not None:
                if self._idempotency_payload[idempotency_key] != fingerprint:
                    raise ConflictError("Idempotency-Key already used with a different payload")
                existing = self.get_investigation(existing_id)
                if existing is None:
                    raise ConflictError("Idempotency mapping missing investigation")
                return existing
            self._by_idempotency[idempotency_key] = investigation.investigation_id
            self._idempotency_payload[idempotency_key] = fingerprint
        with self._engine.begin() as connection:
            connection.execute(
                pg_insert(self._investigations).values(**_investigation_row(investigation))
            )
            connection.execute(
                pg_insert(self._restrictions).values(**_restriction_row(restriction))
            )
        return investigation

    def get_investigation(self, investigation_id: str) -> Investigation | None:
        with self._engine.begin() as connection:
            row = (
                connection.execute(
                    select(self._investigations).where(
                        self._investigations.c.investigation_id == investigation_id
                    )
                )
                .mappings()
                .first()
            )
        return _row_to_investigation(row) if row else None

    def list_investigations(
        self,
        *,
        tenant_id: str,
        case_id: str | None = None,
    ) -> tuple[Investigation, ...]:
        stmt = select(self._investigations).where(self._investigations.c.tenant_id == tenant_id)
        if case_id is not None:
            stmt = stmt.where(self._investigations.c.case_id == case_id)
        with self._engine.begin() as connection:
            rows = connection.execute(stmt).mappings().all()
        items = [_row_to_investigation(row) for row in rows]
        return tuple(sorted(items, key=lambda i: i.created_at, reverse=True))

    def save_investigation(self, investigation: Investigation) -> Investigation:
        with self._engine.begin() as connection:
            result = connection.execute(
                self._investigations.update()
                .where(self._investigations.c.investigation_id == investigation.investigation_id)
                .values(**_investigation_row(investigation))
            )
            if result.rowcount == 0:
                raise ConflictError("Unknown investigation")
        return investigation

    def save_finding(self, finding: Finding) -> Finding:
        with self._engine.begin() as connection:
            connection.execute(pg_insert(self._findings).values(**_finding_row(finding)))
        return finding

    def list_findings(self, investigation_id: str) -> tuple[Finding, ...]:
        with self._engine.begin() as connection:
            rows = (
                connection.execute(
                    select(self._findings).where(
                        self._findings.c.investigation_id == investigation_id
                    )
                )
                .mappings()
                .all()
            )
        return tuple(_row_to_finding(row) for row in rows)

    def get_restriction(self, restriction_id: str) -> RiskRestriction | None:
        with self._engine.begin() as connection:
            row = (
                connection.execute(
                    select(self._restrictions).where(
                        self._restrictions.c.restriction_id == restriction_id
                    )
                )
                .mappings()
                .first()
            )
        return _row_to_restriction(row) if row else None

    def save_restriction(self, restriction: RiskRestriction) -> RiskRestriction:
        if restriction.financial_approval_granted:
            raise ConflictError("Risk store refuses financial_approval_granted=true")
        with self._engine.begin() as connection:
            result = connection.execute(
                self._restrictions.update()
                .where(self._restrictions.c.restriction_id == restriction.restriction_id)
                .values(**_restriction_row(restriction))
            )
            if result.rowcount == 0:
                raise ConflictError("Unknown restriction")
        return restriction

    def list_restrictions(
        self,
        *,
        tenant_id: str,
        case_id: str | None = None,
        investigation_id: str | None = None,
    ) -> tuple[RiskRestriction, ...]:
        stmt = select(self._restrictions).where(self._restrictions.c.tenant_id == tenant_id)
        if case_id is not None:
            stmt = stmt.where(self._restrictions.c.case_id == case_id)
        if investigation_id is not None:
            stmt = stmt.where(self._restrictions.c.investigation_id == investigation_id)
        with self._engine.begin() as connection:
            rows = connection.execute(stmt).mappings().all()
        return tuple(_row_to_restriction(row) for row in rows)


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        return [str(v) for v in json.loads(value)]
    return list(value)


def _investigation_row(investigation: Investigation) -> dict[str, Any]:
    return {
        "investigation_id": investigation.investigation_id,
        "tenant_id": investigation.tenant_id,
        "case_id": investigation.case_id,
        "case_revision": investigation.case_revision,
        "reason_code": investigation.reason_code,
        "status": investigation.status,
        "queue_ref": investigation.queue_ref,
        "owner_principal_id": investigation.owner_principal_id,
        "severity": investigation.severity,
        "created_at": investigation.created_at,
        "updated_at": investigation.updated_at,
        "revision": investigation.revision,
        "finding_ids": list(investigation.finding_ids),
        "restriction_ids": list(investigation.restriction_ids),
        "evidence_ids": list(investigation.evidence_ids),
    }


def _finding_row(finding: Finding) -> dict[str, Any]:
    return {
        "finding_id": finding.finding_id,
        "investigation_id": finding.investigation_id,
        "classification": finding.classification,
        "evidence_ids": list(finding.evidence_ids),
        "notes": finding.notes,
        "recorded_by": finding.recorded_by,
        "recorded_at": finding.recorded_at,
        "revision": finding.revision,
    }


def _restriction_row(restriction: RiskRestriction) -> dict[str, Any]:
    return {
        "restriction_id": restriction.restriction_id,
        "tenant_id": restriction.tenant_id,
        "case_id": restriction.case_id,
        "investigation_id": restriction.investigation_id,
        "reason_code": restriction.reason_code,
        "status": restriction.status,
        "blocks_financial_actions": restriction.blocks_financial_actions,
        "created_at": restriction.created_at,
        "review_due_at": restriction.review_due_at,
        "created_by": restriction.created_by,
        "policy_version": restriction.policy_version,
        "evidence_ids": list(restriction.evidence_ids),
        "revision": restriction.revision,
        "transaction_ref": restriction.transaction_ref,
        "action_id": restriction.action_id,
        "cleared_by": restriction.cleared_by,
        "clearance_reason": restriction.clearance_reason,
        "financial_approval_granted": False,
    }


def _row_to_investigation(row: Any) -> Investigation:
    return Investigation(
        investigation_id=row["investigation_id"],
        tenant_id=row["tenant_id"],
        case_id=row["case_id"],
        case_revision=int(row["case_revision"]),
        reason_code=row["reason_code"],
        status=row["status"],
        queue_ref=row["queue_ref"],
        owner_principal_id=row["owner_principal_id"],
        severity=row["severity"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        revision=int(row["revision"]),
        finding_ids=tuple(_as_list(row["finding_ids"])),
        restriction_ids=tuple(_as_list(row["restriction_ids"])),
        evidence_ids=tuple(_as_list(row["evidence_ids"])),
    )


def _row_to_finding(row: Any) -> Finding:
    return Finding(
        finding_id=row["finding_id"],
        investigation_id=row["investigation_id"],
        classification=row["classification"],
        evidence_ids=tuple(_as_list(row["evidence_ids"])),
        notes=row["notes"],
        recorded_by=row["recorded_by"],
        recorded_at=row["recorded_at"],
        revision=int(row["revision"]),
    )


def _row_to_restriction(row: Any) -> RiskRestriction:
    return RiskRestriction(
        restriction_id=row["restriction_id"],
        tenant_id=row["tenant_id"],
        case_id=row["case_id"],
        investigation_id=row["investigation_id"],
        reason_code=row["reason_code"],
        status=row["status"],
        blocks_financial_actions=bool(row["blocks_financial_actions"]),
        created_at=row["created_at"],
        review_due_at=row["review_due_at"],
        created_by=row["created_by"],
        policy_version=row["policy_version"],
        evidence_ids=tuple(_as_list(row["evidence_ids"])),
        revision=int(row["revision"]),
        transaction_ref=row["transaction_ref"],
        action_id=row["action_id"],
        cleared_by=row["cleared_by"],
        clearance_reason=row["clearance_reason"],
        financial_approval_granted=False,
    )


def _inv_fingerprint(investigation: Investigation) -> str:
    return "|".join(
        [
            investigation.tenant_id,
            investigation.case_id,
            investigation.reason_code,
            investigation.queue_ref,
            str(investigation.case_revision),
        ]
    )
