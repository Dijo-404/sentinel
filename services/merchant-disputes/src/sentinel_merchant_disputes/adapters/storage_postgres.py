"""PostgreSQL dispute store (DISPUTES_DATABASE_URL=postgresql+psycopg://...)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..application.errors import ConfigurationError, ConflictError, PeerUnavailableError
from ..domain.types import DisputeCase, EvidencePacket

SCHEMA = "merchant_disputes"


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("DISPUTES_DATABASE_URL must be PostgreSQL for this adapter")
    return engine


def _tables(schema: str) -> tuple[Table, Table, Table]:
    metadata = MetaData()
    disputes = Table(
        "disputes",
        metadata,
        Column("dispute_id", String(128), primary_key=True),
        Column("tenant_id", String(256), nullable=False),
        Column("merchant_ref", String(256), nullable=False),
        Column("case_id", String(256), nullable=False),
        Column("reason_code", String(128), nullable=False),
        Column("deadline_at", String(64), nullable=False),
        Column("evidence_packet_ids", JSONB, nullable=False),
        Column("status", String(64), nullable=False),
        Column("order_reference", String(256), nullable=False),
        Column("case_revision", Integer, nullable=False),
        schema=schema,
    )
    packets = Table(
        "evidence_packets",
        metadata,
        Column("packet_id", String(128), primary_key=True),
        Column("dispute_id", String(128), nullable=False),
        Column("case_id", String(256), nullable=False),
        Column("evidence_ids", JSONB, nullable=False),
        Column("kinds", JSONB, nullable=False),
        Column("assembled_at", String(64), nullable=False),
        schema=schema,
    )
    idempotency = Table(
        "dispute_idempotency",
        metadata,
        Column("idempotency_key", String(256), primary_key=True),
        Column("dispute_id", String(128), nullable=False),
        Column("fingerprint", String(512), nullable=False),
        schema=schema,
    )
    return disputes, packets, idempotency


def _fingerprint(dispute: DisputeCase) -> str:
    return "|".join(
        [
            dispute.tenant_id,
            dispute.merchant_ref,
            dispute.case_id,
            dispute.reason_code,
            dispute.deadline_at,
            dispute.order_reference,
        ]
    )


def _dispute_row(dispute: DisputeCase) -> dict[str, Any]:
    return {
        "dispute_id": dispute.dispute_id,
        "tenant_id": dispute.tenant_id,
        "merchant_ref": dispute.merchant_ref,
        "case_id": dispute.case_id,
        "reason_code": dispute.reason_code,
        "deadline_at": dispute.deadline_at,
        "evidence_packet_ids": list(dispute.evidence_packet_ids),
        "status": dispute.status,
        "order_reference": dispute.order_reference,
        "case_revision": dispute.case_revision,
    }


def _dispute_from(row: dict[str, Any]) -> DisputeCase:
    return DisputeCase(
        dispute_id=str(row["dispute_id"]),
        tenant_id=str(row["tenant_id"]),
        merchant_ref=str(row["merchant_ref"]),
        case_id=str(row["case_id"]),
        reason_code=str(row["reason_code"]),
        deadline_at=str(row["deadline_at"]),
        evidence_packet_ids=tuple(row.get("evidence_packet_ids") or ()),
        status=row["status"],
        order_reference=str(row.get("order_reference") or ""),
        case_revision=int(row.get("case_revision") or 1),
    )


def _packet_row(packet: EvidencePacket) -> dict[str, Any]:
    return {
        "packet_id": packet.packet_id,
        "dispute_id": packet.dispute_id,
        "case_id": packet.case_id,
        "evidence_ids": list(packet.evidence_ids),
        "kinds": list(packet.kinds),
        "assembled_at": packet.assembled_at,
    }


def _packet_from(row: dict[str, Any]) -> EvidencePacket:
    return EvidencePacket(
        packet_id=str(row["packet_id"]),
        dispute_id=str(row["dispute_id"]),
        case_id=str(row["case_id"]),
        evidence_ids=tuple(row.get("evidence_ids") or ()),
        kinds=tuple(row.get("kinds") or ()),
        assembled_at=str(row["assembled_at"]),
    )


class PostgresDisputeStore:
    def __init__(self, engine: Engine, schema: str = SCHEMA) -> None:
        if engine.dialect.name != "postgresql":
            raise ConfigurationError("A real PostgreSQL connection is required")
        self._engine = engine
        self._schema = schema
        self._disputes, self._packets, self._idempotency = _tables(schema)

    def migrate(self) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"'))
                self._disputes.create(connection, checkfirst=True)
                self._packets.create(connection, checkfirst=True)
                self._idempotency.create(connection, checkfirst=True)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("dispute database unavailable") from exc

    def create(self, dispute: DisputeCase, *, idempotency_key: str | None) -> DisputeCase:
        try:
            with self._engine.begin() as connection:
                if idempotency_key:
                    fingerprint = _fingerprint(dispute)
                    existing = (
                        connection.execute(
                            select(self._idempotency).where(
                                self._idempotency.c.idempotency_key == idempotency_key
                            )
                        )
                        .mappings()
                        .first()
                    )
                    if existing is not None:
                        if existing["fingerprint"] != fingerprint:
                            raise ConflictError(
                                "Idempotency-Key already used with a different payload"
                            )
                        row = (
                            connection.execute(
                                select(self._disputes).where(
                                    self._disputes.c.dispute_id == existing["dispute_id"]
                                )
                            )
                            .mappings()
                            .first()
                        )
                        if row is None:
                            raise ConflictError("Idempotency mapping missing dispute")
                        return _dispute_from(dict(row))
                    connection.execute(
                        self._idempotency.insert().values(
                            idempotency_key=idempotency_key,
                            dispute_id=dispute.dispute_id,
                            fingerprint=fingerprint,
                        )
                    )
                connection.execute(self._disputes.insert().values(**_dispute_row(dispute)))
        except ConflictError:
            raise
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("dispute database unavailable") from exc
        return dispute

    def get(self, dispute_id: str) -> DisputeCase | None:
        try:
            with self._engine.begin() as connection:
                row = (
                    connection.execute(
                        select(self._disputes).where(self._disputes.c.dispute_id == dispute_id)
                    )
                    .mappings()
                    .first()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("dispute database unavailable") from exc
        if row is None:
            return None
        return _dispute_from(dict(row))

    def list(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
    ) -> tuple[DisputeCase, ...]:
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._disputes)
                        .where(
                            self._disputes.c.tenant_id == tenant_id,
                            self._disputes.c.merchant_ref == merchant_ref,
                        )
                        .order_by(self._disputes.c.dispute_id)
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("dispute database unavailable") from exc
        return tuple(_dispute_from(dict(row)) for row in rows)

    def save(self, dispute: DisputeCase) -> DisputeCase:
        try:
            with self._engine.begin() as connection:
                existing = (
                    connection.execute(
                        select(self._disputes.c.dispute_id).where(
                            self._disputes.c.dispute_id == dispute.dispute_id
                        )
                    )
                    .mappings()
                    .first()
                )
                if existing is None:
                    raise ConflictError("Unknown dispute")
                connection.execute(
                    self._disputes.update()
                    .where(self._disputes.c.dispute_id == dispute.dispute_id)
                    .values(**_dispute_row(dispute))
                )
        except ConflictError:
            raise
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("dispute database unavailable") from exc
        return dispute

    def save_packet(self, packet: EvidencePacket) -> EvidencePacket:
        values = _packet_row(packet)
        try:
            with self._engine.begin() as connection:
                stmt = pg_insert(self._packets).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["packet_id"],
                    set_={
                        "dispute_id": stmt.excluded.dispute_id,
                        "case_id": stmt.excluded.case_id,
                        "evidence_ids": stmt.excluded.evidence_ids,
                        "kinds": stmt.excluded.kinds,
                        "assembled_at": stmt.excluded.assembled_at,
                    },
                )
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("dispute database unavailable") from exc
        return packet

    def list_packets(self, dispute_id: str) -> tuple[EvidencePacket, ...]:
        dispute = self.get(dispute_id)
        if dispute is None:
            return ()
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._packets).where(self._packets.c.dispute_id == dispute_id)
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("dispute database unavailable") from exc
        packets = [_packet_from(dict(row)) for row in rows]
        by_id = {packet.packet_id: packet for packet in packets}
        return tuple(
            by_id[packet_id] for packet_id in dispute.evidence_packet_ids if packet_id in by_id
        )
