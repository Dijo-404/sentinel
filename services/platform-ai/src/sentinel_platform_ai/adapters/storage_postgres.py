"""PostgreSQL platform-ai store (PLATFORM_AI_DATABASE_URL)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
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
from ..domain.types import AiConfig, AiIntegration, AiModel, AiRun

SCHEMA = "platform_ai"


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("PLATFORM_AI_DATABASE_URL must be PostgreSQL")
    return engine


def _tables(schema: str) -> tuple[Table, Table, Table]:
    metadata = MetaData()
    configs = Table(
        "ai_configs",
        metadata,
        Column("tenant_id", String(256), primary_key=True),
        Column("models", JSONB, nullable=False),
        Column("kill_switch", Boolean, nullable=False),
        Column("updated_at", String(64), nullable=False),
        schema=schema,
    )
    runs = Table(
        "ai_runs",
        metadata,
        Column("run_id", String(128), primary_key=True),
        Column("tenant_id", String(256), nullable=False),
        Column("model_id", String(256), nullable=False),
        Column("status", String(64), nullable=False),
        Column("started_at", String(64), nullable=False),
        schema=schema,
    )
    integrations = Table(
        "ai_integrations",
        metadata,
        Column("integration_id", String(128), primary_key=True),
        Column("tenant_id", String(256), nullable=False),
        Column("name", String(256), nullable=False),
        Column("status", String(64), nullable=False),
        Column("updated_at", String(64), nullable=False),
        schema=schema,
    )
    return configs, runs, integrations


class PostgresPlatformAiStore:
    def __init__(self, engine: Engine, schema: str = SCHEMA) -> None:
        if engine.dialect.name != "postgresql":
            raise ConfigurationError("A real PostgreSQL connection is required")
        self._engine = engine
        self._schema = schema
        self._configs, self._runs, self._integrations = _tables(schema)

    def migrate(self) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"'))
                self._configs.create(connection, checkfirst=True)
                self._runs.create(connection, checkfirst=True)
                self._integrations.create(connection, checkfirst=True)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("platform-ai database unavailable") from exc

    def get_config(self, tenant_id: str) -> AiConfig | None:
        try:
            with self._engine.begin() as connection:
                row = (
                    connection.execute(
                        select(self._configs).where(self._configs.c.tenant_id == tenant_id)
                    )
                    .mappings()
                    .first()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("platform-ai database unavailable") from exc
        if row is None:
            return None
        return _config_from(dict(row))

    def put_config(self, config: AiConfig) -> AiConfig:
        values = _config_row(config)
        try:
            with self._engine.begin() as connection:
                stmt = pg_insert(self._configs).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[self._configs.c.tenant_id],
                    set_={
                        "models": stmt.excluded.models,
                        "kill_switch": stmt.excluded.kill_switch,
                        "updated_at": stmt.excluded.updated_at,
                    },
                )
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("platform-ai database unavailable") from exc
        return config

    def list_runs(self, tenant_id: str) -> tuple[AiRun, ...]:
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._runs)
                        .where(self._runs.c.tenant_id == tenant_id)
                        .order_by(self._runs.c.started_at.desc())
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("platform-ai database unavailable") from exc
        return tuple(_run_from(dict(row)) for row in rows)

    def put_run(self, run: AiRun) -> AiRun:
        values = _run_row(run)
        try:
            with self._engine.begin() as connection:
                stmt = pg_insert(self._runs).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[self._runs.c.run_id],
                    set_={
                        "tenant_id": stmt.excluded.tenant_id,
                        "model_id": stmt.excluded.model_id,
                        "status": stmt.excluded.status,
                        "started_at": stmt.excluded.started_at,
                    },
                )
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("platform-ai database unavailable") from exc
        return run

    def list_integrations(self, tenant_id: str) -> tuple[AiIntegration, ...]:
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._integrations)
                        .where(self._integrations.c.tenant_id == tenant_id)
                        .order_by(self._integrations.c.updated_at.desc())
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("platform-ai database unavailable") from exc
        return tuple(_integration_from(dict(row)) for row in rows)

    def put_integration(self, integration: AiIntegration) -> AiIntegration:
        values = _integration_row(integration)
        try:
            with self._engine.begin() as connection:
                stmt = pg_insert(self._integrations).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[self._integrations.c.integration_id],
                    set_={
                        "tenant_id": stmt.excluded.tenant_id,
                        "name": stmt.excluded.name,
                        "status": stmt.excluded.status,
                        "updated_at": stmt.excluded.updated_at,
                    },
                )
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("platform-ai database unavailable") from exc
        return integration


def _config_row(config: AiConfig) -> dict[str, Any]:
    return {
        "tenant_id": config.tenant_id,
        "models": [model.to_wire() for model in config.models],
        "kill_switch": config.kill_switch,
        "updated_at": config.updated_at,
    }


def _config_from(row: dict[str, Any]) -> AiConfig:
    models_raw = row.get("models") or []
    models = tuple(
        AiModel(
            model_id=str(item["model_id"]),
            label=str(item.get("label") or item["model_id"]),
            provider=str(item.get("provider") or "sandbox"),
        )
        for item in models_raw
    )
    return AiConfig(
        tenant_id=str(row["tenant_id"]),
        models=models,
        kill_switch=bool(row["kill_switch"]),
        updated_at=str(row["updated_at"]),
    )


def _run_row(run: AiRun) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "tenant_id": run.tenant_id,
        "model_id": run.model_id,
        "status": run.status,
        "started_at": run.started_at,
    }


def _run_from(row: dict[str, Any]) -> AiRun:
    return AiRun(
        run_id=str(row["run_id"]),
        tenant_id=str(row["tenant_id"]),
        model_id=str(row["model_id"]),
        status=str(row["status"]),
        started_at=str(row["started_at"]),
    )


def _integration_row(integration: AiIntegration) -> dict[str, Any]:
    return {
        "integration_id": integration.integration_id,
        "tenant_id": integration.tenant_id,
        "name": integration.name,
        "status": integration.status,
        "updated_at": integration.updated_at,
    }


def _integration_from(row: dict[str, Any]) -> AiIntegration:
    return AiIntegration(
        integration_id=str(row["integration_id"]),
        tenant_id=str(row["tenant_id"]),
        name=str(row["name"]),
        status=str(row["status"]),
        updated_at=str(row["updated_at"]),
    )
