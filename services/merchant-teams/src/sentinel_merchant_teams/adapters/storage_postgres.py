"""PostgreSQL staff store (MERCHANT_TEAMS_DATABASE_URL)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..application.errors import ConfigurationError, PeerUnavailableError
from ..domain.types import MerchantSettings, MerchantStaff, StaffActivity

SCHEMA = "merchant_teams"
STAFF_TABLE = "merchant_staff"
ACTIVITY_TABLE = "staff_activity"
SETTINGS_TABLE = "merchant_settings"

SANDBOX_TENANT_ID = "tenant-demo"
SANDBOX_MERCHANT_REF = "merchant-demo-1"
SANDBOX_STAFF_ID = "staff-demo-1"


def build_engine(database_url: str) -> Engine:
    engine = create_engine(database_url, hide_parameters=True)
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("MERCHANT_TEAMS_DATABASE_URL must be PostgreSQL")
    return engine


def _staff_table(schema: str = SCHEMA) -> Table:
    metadata = MetaData()
    return Table(
        STAFF_TABLE,
        metadata,
        Column("staff_id", String(256), primary_key=True),
        Column("tenant_id", String(256), nullable=False),
        Column("merchant_ref", String(256), nullable=False),
        Column("display_name", String(512), nullable=False),
        Column("roles_json", JSONB, nullable=False),
        Column("approval_limit_minor", BigInteger, nullable=True),
        Column("currency", String(16), nullable=True),
        Column("active", Boolean, nullable=False, server_default=text("TRUE")),
        schema=schema,
    )


def _activity_table(schema: str = SCHEMA) -> Table:
    metadata = MetaData()
    return Table(
        ACTIVITY_TABLE,
        metadata,
        Column("event_id", String(256), primary_key=True),
        Column("staff_id", String(256), nullable=False),
        Column("at", String(64), nullable=False),
        Column("kind", String(128), nullable=False),
        Column("subject_ref", String(256), nullable=False),
        Column("summary", String(1024), nullable=False),
        schema=schema,
    )


def _settings_table(schema: str = SCHEMA) -> Table:
    metadata = MetaData()
    return Table(
        SETTINGS_TABLE,
        metadata,
        Column("tenant_id", String(256), primary_key=True),
        Column("merchant_ref", String(256), primary_key=True),
        Column("notification_language", String(32), nullable=False),
        Column("notify_disputes", Boolean, nullable=False, server_default=text("TRUE")),
        Column("notify_settlements", Boolean, nullable=False, server_default=text("TRUE")),
        schema=schema,
    )


class PostgresStaffStore:
    def __init__(self, engine: Engine, schema: str = SCHEMA) -> None:
        if engine.dialect.name != "postgresql":
            raise ConfigurationError("A real PostgreSQL connection is required")
        self._engine = engine
        self._schema = schema
        self._staff = _staff_table(schema)
        self._activity = _activity_table(schema)
        self._settings = _settings_table(schema)

    @classmethod
    def from_url(cls, database_url: str) -> PostgresStaffStore:
        return cls(build_engine(database_url))

    def migrate(self) -> None:
        try:
            with self._engine.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"'))
                self._staff.create(connection, checkfirst=True)
                self._activity.create(connection, checkfirst=True)
                self._settings.create(connection, checkfirst=True)
                connection.execute(
                    text(
                        f"CREATE INDEX IF NOT EXISTS ix_merchant_staff_tenant_merchant "
                        f'ON "{self._schema}"."{STAFF_TABLE}" (tenant_id, merchant_ref)'
                    )
                )
                connection.execute(
                    text(
                        f"CREATE INDEX IF NOT EXISTS ix_staff_activity_staff_id "
                        f'ON "{self._schema}"."{ACTIVITY_TABLE}" (staff_id)'
                    )
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("merchant-teams database unavailable") from exc

    def create(self, staff: MerchantStaff) -> MerchantStaff:
        values = _staff_to_row(staff)
        try:
            with self._engine.begin() as connection:
                connection.execute(self._staff.insert().values(**values))
        except IntegrityError as exc:
            raise ValueError("staff_id already exists") from exc
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("merchant-teams database unavailable") from exc
        return staff

    def get(self, *, tenant_id: str, staff_id: str) -> MerchantStaff | None:
        try:
            with self._engine.begin() as connection:
                row = (
                    connection.execute(
                        select(self._staff).where(
                            self._staff.c.tenant_id == tenant_id,
                            self._staff.c.staff_id == staff_id,
                        )
                    )
                    .mappings()
                    .first()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("merchant-teams database unavailable") from exc
        if row is None:
            return None
        return _row_to_staff(dict(row))

    def save(self, staff: MerchantStaff) -> MerchantStaff:
        values = _staff_to_row(staff)
        try:
            with self._engine.begin() as connection:
                stmt = pg_insert(self._staff).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["staff_id"],
                    set_={
                        "tenant_id": stmt.excluded.tenant_id,
                        "merchant_ref": stmt.excluded.merchant_ref,
                        "display_name": stmt.excluded.display_name,
                        "roles_json": stmt.excluded.roles_json,
                        "approval_limit_minor": stmt.excluded.approval_limit_minor,
                        "currency": stmt.excluded.currency,
                        "active": stmt.excluded.active,
                    },
                )
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("merchant-teams database unavailable") from exc
        return staff

    def list_for_merchant(self, *, tenant_id: str, merchant_ref: str) -> tuple[MerchantStaff, ...]:
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._staff)
                        .where(
                            self._staff.c.tenant_id == tenant_id,
                            self._staff.c.merchant_ref == merchant_ref,
                        )
                        .order_by(self._staff.c.staff_id)
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("merchant-teams database unavailable") from exc
        return tuple(_row_to_staff(dict(row)) for row in rows)

    def append_activity(self, event: StaffActivity) -> StaffActivity:
        values = _activity_to_row(event)
        try:
            with self._engine.begin() as connection:
                connection.execute(self._activity.insert().values(**values))
        except IntegrityError as exc:
            raise ValueError("event_id already exists") from exc
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("merchant-teams database unavailable") from exc
        return event

    def list_activity(self, *, staff_id: str) -> tuple[StaffActivity, ...]:
        try:
            with self._engine.begin() as connection:
                rows = (
                    connection.execute(
                        select(self._activity)
                        .where(self._activity.c.staff_id == staff_id)
                        .order_by(self._activity.c.at, self._activity.c.event_id)
                    )
                    .mappings()
                    .all()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("merchant-teams database unavailable") from exc
        return tuple(_row_to_activity(dict(row)) for row in rows)

    def get_settings(self, *, tenant_id: str, merchant_ref: str) -> MerchantSettings | None:
        try:
            with self._engine.begin() as connection:
                row = (
                    connection.execute(
                        select(self._settings).where(
                            self._settings.c.tenant_id == tenant_id,
                            self._settings.c.merchant_ref == merchant_ref,
                        )
                    )
                    .mappings()
                    .first()
                )
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("merchant-teams database unavailable") from exc
        if row is None:
            return None
        return _row_to_settings(dict(row))

    def save_settings(self, settings: MerchantSettings) -> MerchantSettings:
        values = _settings_to_row(settings)
        try:
            with self._engine.begin() as connection:
                stmt = pg_insert(self._settings).values(**values)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["tenant_id", "merchant_ref"],
                    set_={
                        "notification_language": stmt.excluded.notification_language,
                        "notify_disputes": stmt.excluded.notify_disputes,
                        "notify_settlements": stmt.excluded.notify_settlements,
                    },
                )
                connection.execute(stmt)
        except SQLAlchemyError as exc:
            raise PeerUnavailableError("merchant-teams database unavailable") from exc
        return settings


def _staff_demo_fixture_path() -> Path:
    here = Path(__file__).resolve()
    candidates = (
        here.parents[3] / "fixtures" / "staff_demo.json",
        Path.cwd() / "fixtures" / "staff_demo.json",
    )
    for path in candidates:
        if path.is_file():
            return path
    raise ConfigurationError("fixtures/staff_demo.json not found for sandbox seed")


def seed_merchant_demo_membership(database_url: str) -> dict[str, Any]:
    """Idempotent sandbox seed: tenant-demo / merchant-demo-1 membership + activity."""
    fixture = json.loads(_staff_demo_fixture_path().read_text(encoding="utf-8"))
    staff_body = fixture["staff"]
    if staff_body["tenant_id"] != SANDBOX_TENANT_ID:
        raise ConfigurationError("sandbox seed requires tenant-demo")
    if staff_body["merchant_ref"] != SANDBOX_MERCHANT_REF:
        raise ConfigurationError("sandbox seed requires merchant-demo-1")
    if staff_body["staff_id"] != SANDBOX_STAFF_ID:
        raise ConfigurationError("sandbox seed requires staff-demo-1")

    settings_body = fixture.get("settings")
    if not isinstance(settings_body, dict):
        raise ConfigurationError("sandbox seed requires settings object")
    if settings_body.get("tenant_id") != SANDBOX_TENANT_ID:
        raise ConfigurationError("sandbox seed settings require tenant-demo")
    if settings_body.get("merchant_ref") != SANDBOX_MERCHANT_REF:
        raise ConfigurationError("sandbox seed settings require merchant-demo-1")

    store = PostgresStaffStore.from_url(database_url)
    store.migrate()
    staff = MerchantStaff.from_wire(staff_body)
    store.save(staff)
    settings = MerchantSettings.from_wire(settings_body)
    store.save_settings(settings)

    activity_rows = fixture.get("activity") or []
    existing = {event.event_id for event in store.list_activity(staff_id=staff.staff_id)}
    for raw in activity_rows:
        event = StaffActivity(
            event_id=str(raw["event_id"]),
            staff_id=str(raw["staff_id"]),
            at=str(raw["at"]),
            kind=str(raw["kind"]),
            subject_ref=str(raw["subject_ref"]),
            summary=str(raw["summary"]),
        )
        if event.event_id not in existing:
            store.append_activity(event)

    return {
        "status": "PASS",
        "tenant_id": staff.tenant_id,
        "merchant_ref": staff.merchant_ref,
        "staff_id": staff.staff_id,
        "settings_merchant_ref": settings.merchant_ref,
        "evidence_label": "synthetic_seed",
    }


def _staff_to_row(staff: MerchantStaff) -> dict[str, Any]:
    return {
        "staff_id": staff.staff_id,
        "tenant_id": staff.tenant_id,
        "merchant_ref": staff.merchant_ref,
        "display_name": staff.display_name,
        "roles_json": list(staff.roles),
        "approval_limit_minor": staff.approval_limit_minor,
        "currency": staff.currency,
        "active": staff.active,
    }


def _row_to_staff(row: dict[str, Any]) -> MerchantStaff:
    roles = row["roles_json"]
    if isinstance(roles, str):
        roles = json.loads(roles)
    return MerchantStaff(
        staff_id=str(row["staff_id"]),
        tenant_id=str(row["tenant_id"]),
        merchant_ref=str(row["merchant_ref"]),
        display_name=str(row["display_name"]),
        roles=tuple(str(r) for r in roles),
        active=bool(row["active"]),
        approval_limit_minor=(
            int(row["approval_limit_minor"]) if row["approval_limit_minor"] is not None else None
        ),
        currency=str(row["currency"]) if row["currency"] is not None else None,
    )


def _activity_to_row(event: StaffActivity) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "staff_id": event.staff_id,
        "at": event.at,
        "kind": event.kind,
        "subject_ref": event.subject_ref,
        "summary": event.summary,
    }


def _row_to_activity(row: dict[str, Any]) -> StaffActivity:
    return StaffActivity(
        event_id=str(row["event_id"]),
        staff_id=str(row["staff_id"]),
        at=str(row["at"]),
        kind=str(row["kind"]),
        subject_ref=str(row["subject_ref"]),
        summary=str(row["summary"]),
    )


def _settings_to_row(settings: MerchantSettings) -> dict[str, Any]:
    return {
        "tenant_id": settings.tenant_id,
        "merchant_ref": settings.merchant_ref,
        "notification_language": settings.notification_language,
        "notify_disputes": settings.notify_disputes,
        "notify_settlements": settings.notify_settlements,
    }


def _row_to_settings(row: dict[str, Any]) -> MerchantSettings:
    return MerchantSettings(
        tenant_id=str(row["tenant_id"]),
        merchant_ref=str(row["merchant_ref"]),
        notification_language=str(row["notification_language"]),
        notify_disputes=bool(row["notify_disputes"]),
        notify_settlements=bool(row["notify_settlements"]),
    )
