"""PostgreSQL merchant metrics snapshot store (MERCHANT_ANALYTICS_DATABASE_URL)."""

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

from ..application.errors import ConfigurationError, PeerUnavailableError
from ..domain.types import MerchantMetrics

SCHEMA = "merchant_analytics"
TABLE = "merchant_metrics_snapshots"


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("MERCHANT_ANALYTICS_DATABASE_URL must be PostgreSQL")
    return engine


def _table(schema: str = SCHEMA) -> Table:
    metadata = MetaData()
    return Table(
        TABLE,
        metadata,
        Column("tenant_id", String(256), primary_key=True),
        Column("merchant_ref", String(256), primary_key=True),
        Column("window_start", String(64), primary_key=True),
        Column("window_end", String(64), primary_key=True),
        Column("exception_rate", String(32), nullable=False),
        Column("unresolved_minor", Integer, nullable=False),
        Column("currency", String(16), nullable=False),
        Column("refund_aging_buckets", JSONB, nullable=False),
        Column("median_handling_seconds", Integer, nullable=False),
        Column("top_causes", JSONB, nullable=False),
        schema=schema,
    )


class PostgresMetricsSnapshotStore:
    def __init__(self, engine: Engine, schema: str = SCHEMA) -> None:
        if engine.dialect.name != "postgresql":
            raise ConfigurationError("A real PostgreSQL connection is required")
        self._engine = engine
        self._schema = schema
        self._table = _table(schema)

    def migrate(self) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"'))
                self._table.create(connection, checkfirst=True)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("metrics snapshot database unavailable") from exc

    def get(
        self,
        *,
        tenant_id: str,
        merchant_ref: str,
        window_start: str,
        window_end: str,
    ) -> MerchantMetrics | None:
        try:
            with self._engine.begin() as connection:
                row = (
                    connection.execute(
                        select(self._table).where(
                            self._table.c.tenant_id == tenant_id,
                            self._table.c.merchant_ref == merchant_ref,
                            self._table.c.window_start == window_start,
                            self._table.c.window_end == window_end,
                        )
                    )
                    .mappings()
                    .first()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("metrics snapshot database unavailable") from exc
        if row is None:
            return None
        return _row_to_metrics(dict(row))

    def put(self, metrics: MerchantMetrics) -> None:
        values = _metrics_to_row(metrics)
        try:
            with self._engine.begin() as connection:
                stmt = pg_insert(self._table).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[
                        "tenant_id",
                        "merchant_ref",
                        "window_start",
                        "window_end",
                    ],
                    set_={
                        "exception_rate": stmt.excluded.exception_rate,
                        "unresolved_minor": stmt.excluded.unresolved_minor,
                        "currency": stmt.excluded.currency,
                        "refund_aging_buckets": stmt.excluded.refund_aging_buckets,
                        "median_handling_seconds": stmt.excluded.median_handling_seconds,
                        "top_causes": stmt.excluded.top_causes,
                    },
                )
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("metrics snapshot database unavailable") from exc


def _metrics_to_row(metrics: MerchantMetrics) -> dict[str, Any]:
    return {
        "tenant_id": metrics.tenant_id,
        "merchant_ref": metrics.merchant_ref,
        "window_start": metrics.window_start,
        "window_end": metrics.window_end,
        "exception_rate": metrics.exception_rate,
        "unresolved_minor": metrics.unresolved_minor,
        "currency": metrics.currency,
        "refund_aging_buckets": dict(metrics.refund_aging_buckets),
        "median_handling_seconds": metrics.median_handling_seconds,
        "top_causes": list(metrics.top_causes),
    }


def _row_to_metrics(row: dict[str, Any]) -> MerchantMetrics:
    return MerchantMetrics(
        tenant_id=row["tenant_id"],
        merchant_ref=row["merchant_ref"],
        window_start=row["window_start"],
        window_end=row["window_end"],
        exception_rate=row["exception_rate"],
        unresolved_minor=int(row["unresolved_minor"]),
        currency=row["currency"],
        refund_aging_buckets={str(k): int(v) for k, v in dict(row["refund_aging_buckets"]).items()},
        median_handling_seconds=int(row["median_handling_seconds"]),
        top_causes=tuple(str(c) for c in list(row["top_causes"])),
    )
