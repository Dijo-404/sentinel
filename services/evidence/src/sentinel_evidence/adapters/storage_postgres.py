"""PostgreSQL evidence persistence with tenant-scoped rows."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    Connection,
    DateTime,
    Engine,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    delete,
    insert,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from ..application.errors import ConfigurationError
from ..domain.types import CollectRequest, Evidence, EvidenceBundle, Principal


def evidence_tables(schema: str) -> tuple[Table, Table]:
    metadata = MetaData()
    bundles = Table(
        "evidence_bundles",
        metadata,
        Column("tenant_id", String(256), primary_key=True),
        Column("case_id", String(256), primary_key=True),
        Column("case_revision", Integer, nullable=False),
        Column("order_reference", String(256), nullable=False),
        Column("contract_version", String(128), nullable=False),
        Column("reconciliation_codes", JSONB, nullable=False),
        Column("collected_at", DateTime(timezone=True), nullable=False),
        schema=schema,
    )
    items = Table(
        "evidence_items",
        metadata,
        Column("tenant_id", String(256), primary_key=True),
        Column("case_id", String(256), primary_key=True),
        Column("evidence_id", String(256), primary_key=True),
        Column("source", String(256), nullable=False),
        Column("subject_ref", String(256), nullable=False),
        Column("observed_at", String(64), nullable=False),
        Column("expires_at", String(64), nullable=False),
        Column("digest", String(64), nullable=False),
        Column("verification_status", String(32), nullable=False),
        Column("facts", JSONB, nullable=False),
        Column("payload_utf8", LargeBinary, nullable=False),
        schema=schema,
    )
    return bundles, items


class PostgresEvidenceStore:
    def __init__(self, engine: Engine, schema: str = "evidence"):
        if engine.dialect.name != "postgresql":
            raise ConfigurationError("A real PostgreSQL connection is required")
        self._engine = engine
        self._schema = schema
        self._bundles, self._items = evidence_tables(schema)

    def migrate(self) -> None:
        with self._engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"'))
            self._bundles.create(connection, checkfirst=True)
            self._items.create(connection, checkfirst=True)

    def save_bundle(
        self,
        *,
        principal: Principal,
        request: CollectRequest,
        bundle: EvidenceBundle,
    ) -> EvidenceBundle:
        with self._engine.begin() as connection:
            self._set_tenant(connection, principal.tenant_id)
            connection.execute(
                delete(self._items).where(
                    self._items.c.tenant_id == principal.tenant_id,
                    self._items.c.case_id == bundle.case_id,
                )
            )
            connection.execute(
                delete(self._bundles).where(
                    self._bundles.c.tenant_id == principal.tenant_id,
                    self._bundles.c.case_id == bundle.case_id,
                )
            )
            connection.execute(
                insert(self._bundles).values(
                    tenant_id=principal.tenant_id,
                    case_id=bundle.case_id,
                    case_revision=request.case_revision,
                    order_reference=request.order_reference,
                    contract_version=bundle.contract_version,
                    reconciliation_codes=list(bundle.reconciliation_codes),
                    collected_at=datetime.now(UTC),
                )
            )
            for item in bundle.evidence:
                connection.execute(
                    insert(self._items).values(
                        tenant_id=principal.tenant_id,
                        case_id=item.case_id,
                        evidence_id=item.evidence_id,
                        source=item.source,
                        subject_ref=item.subject_ref,
                        observed_at=item.observed_at,
                        expires_at=item.expires_at,
                        digest=item.digest,
                        verification_status=item.verification_status,
                        facts=item.facts,
                        payload_utf8=item.payload_utf8,
                    )
                )
        return bundle

    def get_bundle(self, *, principal: Principal, case_id: str) -> EvidenceBundle | None:
        with self._engine.begin() as connection:
            self._set_tenant(connection, principal.tenant_id)
            bundle_row = (
                connection.execute(
                    select(self._bundles).where(
                        self._bundles.c.tenant_id == principal.tenant_id,
                        self._bundles.c.case_id == case_id,
                    )
                )
                .mappings()
                .first()
            )
            if bundle_row is None:
                return None
            item_rows = (
                connection.execute(
                    select(self._items)
                    .where(
                        self._items.c.tenant_id == principal.tenant_id,
                        self._items.c.case_id == case_id,
                    )
                    .order_by(self._items.c.evidence_id)
                )
                .mappings()
                .all()
            )
        evidence = tuple(
            Evidence(
                evidence_id=row["evidence_id"],
                case_id=row["case_id"],
                source=row["source"],
                subject_ref=row["subject_ref"],
                observed_at=row["observed_at"],
                expires_at=row["expires_at"],
                digest=row["digest"],
                verification_status=row["verification_status"],
                facts=row["facts"] if isinstance(row["facts"], dict) else json.loads(row["facts"]),
                payload_utf8=bytes(row["payload_utf8"]),
            )
            for row in item_rows
        )
        codes = bundle_row["reconciliation_codes"]
        if isinstance(codes, str):
            codes = json.loads(codes)
        return EvidenceBundle(
            contract_version=bundle_row["contract_version"],
            case_id=case_id,
            evidence=evidence,
            reconciliation_codes=tuple(codes),
        )

    def _set_tenant(self, connection: Connection, tenant_id: str) -> None:
        if not tenant_id or "\x00" in tenant_id or len(tenant_id) > 256:
            raise ConfigurationError("Authenticated tenant context is required")
        connection.execute(
            text("SELECT set_config('sentinel.tenant_id', :tenant, true)"),
            {"tenant": tenant_id},
        )
