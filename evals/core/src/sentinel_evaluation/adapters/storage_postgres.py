"""PostgreSQL RunReport store (EVALUATION_DATABASE_URL)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Column, MetaData, String, Table, create_engine, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from sentinel_evaluation.application.errors import ConfigurationError, PeerUnavailableError

SCHEMA = "evaluation"


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("EVALUATION_DATABASE_URL must be PostgreSQL")
    return engine


def _table(schema: str) -> Table:
    metadata = MetaData()
    return Table(
        "run_reports",
        metadata,
        Column("run_id", String(128), primary_key=True),
        Column("payload", JSONB, nullable=False),
        schema=schema,
    )


class PostgresReportStore:
    def __init__(self, engine: Engine, schema: str = SCHEMA) -> None:
        if engine.dialect.name != "postgresql":
            raise ConfigurationError("A real PostgreSQL connection is required")
        self._engine = engine
        self._schema = schema
        self._reports = _table(schema)

    def migrate(self) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"'))
                self._reports.create(connection, checkfirst=True)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("evaluation database unavailable") from exc

    def put_report(self, report: dict[str, Any]) -> dict[str, Any]:
        run_id = str(report["run_id"])
        values = {"run_id": run_id, "payload": dict(report)}
        try:
            with self._engine.begin() as connection:
                stmt = pg_insert(self._reports).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[self._reports.c.run_id],
                    set_={"payload": stmt.excluded.payload},
                )
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("evaluation database unavailable") from exc
        return dict(report)

    def get_report(self, run_id: str) -> dict[str, Any] | None:
        try:
            with self._engine.begin() as connection:
                row = (
                    connection.execute(
                        select(self._reports.c.payload).where(self._reports.c.run_id == run_id)
                    )
                    .mappings()
                    .first()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("evaluation database unavailable") from exc
        if row is None:
            return None
        payload = row["payload"]
        return dict(payload) if isinstance(payload, dict) else None

    def list_reports(self) -> tuple[dict[str, Any], ...]:
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._reports.c.payload).order_by(self._reports.c.run_id.asc())
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("evaluation database unavailable") from exc
        out: list[dict[str, Any]] = []
        for row in rows:
            payload = row["payload"]
            if isinstance(payload, dict):
                out.append(dict(payload))
        return tuple(out)
