"""PostgreSQL activity store (OPS_ACTIVITY_DATABASE_URL)."""

from __future__ import annotations

from sqlalchemy import (
    Column,
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
from ..domain.types import ActivityItem

SCHEMA = "ops_activity"
TABLE = "activity_items"


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("OPS_ACTIVITY_DATABASE_URL must be PostgreSQL")
    return engine


def _table(schema: str = SCHEMA) -> Table:
    metadata = MetaData()
    return Table(
        TABLE,
        metadata,
        Column("activity_id", String(128), primary_key=True),
        Column("tenant_id", String(256), nullable=False),
        Column("kind", String(128), nullable=False),
        Column("summary", Text, nullable=False),
        Column("occurred_at", String(64), nullable=False),
        Column("case_id", String(256), nullable=True),
        schema=schema,
    )


class PostgresActivityStore:
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
            raise PeerUnavailableError("activity database unavailable") from exc

    def put(self, item: ActivityItem) -> None:
        values = {
            "activity_id": item.activity_id,
            "tenant_id": item.tenant_id,
            "kind": item.kind,
            "summary": item.summary,
            "occurred_at": item.occurred_at,
            "case_id": item.case_id,
        }
        stmt = pg_insert(self._table).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["activity_id"],
            set_={
                "tenant_id": stmt.excluded.tenant_id,
                "kind": stmt.excluded.kind,
                "summary": stmt.excluded.summary,
                "occurred_at": stmt.excluded.occurred_at,
                "case_id": stmt.excluded.case_id,
            },
        )
        try:
            with self._engine.begin() as connection:
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("activity database unavailable") from exc

    def list_activity(self, tenant_id: str, *, limit: int) -> list[ActivityItem]:
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._table)
                        .where(self._table.c.tenant_id == tenant_id)
                        .order_by(self._table.c.occurred_at.desc())
                        .limit(limit)
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("activity database unavailable") from exc
        return [
            ActivityItem(
                activity_id=row["activity_id"],
                tenant_id=row["tenant_id"],
                kind=row["kind"],
                summary=row["summary"],
                occurred_at=row["occurred_at"],
                case_id=row["case_id"],
            )
            for row in rows
        ]
