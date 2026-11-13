"""Isolated, synthetic demonstration only; no authoritative financial state."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, text

from .contracts import CONTRACT_VERSION, PORT, CheckReport, ConfigurationError, ServiceSchema
from .postgres import require_postgres, tenant_transaction

RECORDS = (
    ("demo-tenant-a", "shared-record", "synthetic A"),
    ("demo-tenant-b", "shared-record", "synthetic B"),
)
NOTES = (
    ("demo-tenant-a", "shared-note", "shared-record", "synthetic note A"),
    ("demo-tenant-b", "shared-note", "shared-record", "synthetic note B"),
)


def _guard(engine: Engine, service: ServiceSchema, environment: str) -> None:
    require_postgres(engine)
    if (
        environment != "sandbox"
        or not service.schema.startswith("demo_")
        or not (engine.url.database or "").startswith("sentinel_demo_")
    ):
        raise ConfigurationError("Demo mutation requires sandbox, demo_ schema, sentinel_demo_ DB")


def _require_owner(connection: Connection, service: ServiceSchema) -> None:
    row = (
        connection.execute(
            text("""
        SELECT owner.rolname = current_user AS owns_schema,
               runtime.rolcanlogin AND NOT (runtime.rolsuper OR runtime.rolbypassrls
                   OR runtime.rolcreaterole OR runtime.rolcreatedb OR runtime.rolreplication)
                   AS safe_runtime,
               pg_has_role(runtime.oid, owner.oid, 'MEMBER') AS member_of_owner,
               has_schema_privilege(runtime.oid, ns.oid, 'CREATE') AS can_create
          FROM pg_namespace ns
          JOIN pg_roles owner ON owner.oid = ns.nspowner
          JOIN pg_roles runtime ON runtime.rolname = :runtime
         WHERE ns.nspname = :schema
    """),
            {"schema": service.schema, "runtime": service.runtime_role},
        )
        .mappings()
        .one_or_none()
    )
    if not row or not row["owns_schema"] or not row["safe_runtime"]:
        raise ConfigurationError(
            "Migrate as schema owner with a separate unprivileged runtime login"
        )
    if row["member_of_owner"] or row["can_create"]:
        raise ConfigurationError("Runtime must have no ownership membership or schema CREATE grant")
    dangerous_membership = connection.execute(
        text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_roles r WHERE (r.rolsuper OR r.rolbypassrls OR r.rolcreaterole
                OR r.rolcreatedb OR r.rolreplication)
                AND pg_has_role(CAST(:runtime AS name), r.oid, 'MEMBER')
        )
    """),
        {"runtime": service.runtime_role},
    ).scalar_one()
    if dangerous_membership:
        raise ConfigurationError("Runtime must not be a member of privileged roles")


def migrate_demo(
    engine: Engine, service: ServiceSchema, *, environment: str, revision: str = "head"
) -> None:
    """Upgrade the bundled demo chain, or explicitly downgrade it to base for disposable tests."""
    _guard(engine, service, environment)
    if revision not in {"head", "base"}:
        raise ConfigurationError("Demo migration revision must be head or base")
    with engine.begin() as connection:
        _require_owner(connection, service)
        config = Config()
        config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
        config.attributes.update(connection=connection, service=service)
        if revision == "base":
            if (
                connection.execute(
                    text("SELECT to_regclass(:table)"),
                    {"table": f"{service.schema}.demo_records"},
                ).scalar_one()
                is not None
            ):
                # ALTER holds exclusive locks until commit. Only the owner gets all-row
                # visibility for this check; runtime RLS stays enabled and locked out.
                # A rejected downgrade rolls these FORCE changes back atomically.
                for table in ("demo_records", "demo_notes"):
                    connection.exec_driver_sql(
                        f'ALTER TABLE "{service.schema}"."{table}" NO FORCE ROW LEVEL SECURITY'
                    )
                _locked_fixture_only(connection, service)
            command.downgrade(config, "base")
        else:
            command.upgrade(config, "head")


def _locked_fixture_only(connection: Connection, service: ServiceSchema) -> None:
    # Administrative demo credentials are needed to inspect ALL tenants despite forced RLS.
    connection.execute(text("SET LOCAL row_security = off"))
    connection.exec_driver_sql(
        f'LOCK TABLE "{service.schema}".demo_records, "{service.schema}".demo_notes '
        "IN ACCESS EXCLUSIVE MODE"
    )
    for table, expected in (("demo_records", RECORDS), ("demo_notes", NOTES)):
        existing = connection.exec_driver_sql(f'SELECT * FROM "{service.schema}"."{table}"').all()
        if not set(existing).issubset(set(expected)):
            raise ConfigurationError(
                "Refusing demo mutation: database contains non-fixture records"
            )


def seed_demo(engine: Engine, service: ServiceSchema, *, environment: str) -> None:
    """Idempotently insert exact synthetic examples; refuse any non-fixture data."""
    _guard(engine, service, environment)
    with engine.begin() as connection:
        _locked_fixture_only(connection, service)
        for tenant, record, label in RECORDS:
            connection.execute(
                text(
                    f'INSERT INTO "{service.schema}".demo_records (tenant_id, id, label) '
                    "VALUES (:tenant, :record, :label) ON CONFLICT (tenant_id, id) DO NOTHING"
                ),
                {"tenant": tenant, "record": record, "label": label},
            )
        for tenant, note, record, body in NOTES:
            connection.execute(
                text(
                    f'INSERT INTO "{service.schema}".demo_notes (tenant_id, id, record_id, body) '
                    "VALUES (:tenant, :note, :record, :body) ON CONFLICT (tenant_id, id) DO NOTHING"
                ),
                {"tenant": tenant, "note": note, "record": record, "body": body},
            )


def reset_demo(engine: Engine, service: ServiceSchema, *, environment: str) -> None:
    """Delete only the verified synthetic example set in one owned demo schema."""
    _guard(engine, service, environment)
    with engine.begin() as connection:
        _locked_fixture_only(connection, service)
        connection.exec_driver_sql(f'DELETE FROM "{service.schema}".demo_notes')
        connection.exec_driver_sql(f'DELETE FROM "{service.schema}".demo_records')


def inspect_demo(engine: Engine, service: ServiceSchema, tenant_id: str) -> CheckReport:
    """Exercise a real runtime read. Database errors propagate; there is no fixture fallback."""
    with tenant_transaction(engine, tenant_id) as connection:
        revision = connection.execute(
            text("""
            SELECT obj_description(c.oid) FROM pg_class c
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=:schema AND c.relname='demo_records'
        """),
            {"schema": service.schema},
        ).scalar_one()
        if revision != "persistence-kit.v1:0001_demo_notes":
            raise ConfigurationError("Incompatible or absent demo migration")
        count = connection.execute(
            text(f'SELECT count(*) FROM "{service.schema}".demo_records WHERE tenant_id=:tenant'),
            {"tenant": tenant_id},
        ).scalar_one()
    return CheckReport(
        CONTRACT_VERSION,
        PORT,
        "real-postgresql/synthetic-records",
        service.schema,
        "0001_demo_notes",
        count,
    )
