"""PostgreSQL signal store (OBSERVABILITY_DATABASE_URL)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import (
    Column,
    Float,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..application.errors import ConfigurationError, PeerUnavailableError
from ..domain.types import Signal

SCHEMA = "observability"
TABLE = "signals"


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("OBSERVABILITY_DATABASE_URL must be PostgreSQL")
    return engine


def _table(schema: str = SCHEMA) -> Table:
    metadata = MetaData()
    return Table(
        TABLE,
        metadata,
        Column("signal_id", String(128), primary_key=True),
        Column("tenant_id", String(256), nullable=False),
        Column("kind", String(32), nullable=False),
        Column("name", String(256), nullable=False),
        Column("attributes_json", Text, nullable=False),
        Column("events_json", Text, nullable=False),
        Column("recorded_at", String(64), nullable=False),
        Column("value", Float, nullable=True),
        Column("labels_json", Text, nullable=False, server_default="{}"),
        schema=schema,
    )


class PostgresSignalStore:
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
            raise PeerUnavailableError("observability database unavailable") from exc

    def put(self, item: Signal) -> None:
        values = {
            "signal_id": item.signal_id,
            "tenant_id": item.tenant_id,
            "kind": item.kind,
            "name": item.name,
            "attributes_json": json.dumps(item.attributes, sort_keys=True),
            "events_json": json.dumps(item.events, sort_keys=True),
            "recorded_at": item.recorded_at,
            "value": item.value,
            "labels_json": json.dumps(item.labels, sort_keys=True),
        }
        stmt = pg_insert(self._table).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["signal_id"],
            set_={
                "tenant_id": stmt.excluded.tenant_id,
                "kind": stmt.excluded.kind,
                "name": stmt.excluded.name,
                "attributes_json": stmt.excluded.attributes_json,
                "events_json": stmt.excluded.events_json,
                "recorded_at": stmt.excluded.recorded_at,
                "value": stmt.excluded.value,
                "labels_json": stmt.excluded.labels_json,
            },
        )
        try:
            with self._engine.begin() as connection:
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("observability database unavailable") from exc

    def list_signals(self, tenant_id: str, *, limit: int) -> list[Signal]:
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._table)
                        .where(self._table.c.tenant_id == tenant_id)
                        .order_by(self._table.c.recorded_at.desc())
                        .limit(limit)
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("observability database unavailable") from exc
        return [_row_to_signal(row) for row in rows]


def _row_to_signal(row: Any) -> Signal:
    attributes = json.loads(row["attributes_json"] or "{}")
    events = json.loads(row["events_json"] or "[]")
    labels = json.loads(row["labels_json"] or "{}")
    return Signal(
        signal_id=row["signal_id"],
        tenant_id=row["tenant_id"],
        kind=row["kind"],
        name=row["name"],
        attributes=attributes,
        events=events,
        recorded_at=row["recorded_at"],
        value=row["value"],
        labels=labels,
    )
