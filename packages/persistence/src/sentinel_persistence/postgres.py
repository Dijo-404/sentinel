"""SQLAlchemy boundary; identity must already have been authenticated by the caller."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, text

from .contracts import ConfigurationError, ServiceSchema, identifier


def require_postgres(engine: Engine) -> None:
    if engine.dialect.name != "postgresql":
        raise ConfigurationError("A real PostgreSQL connection is required")


@contextmanager
def tenant_transaction(engine: Engine, tenant_id: str) -> Iterator[Connection]:
    """Commit or roll back one authenticated tenant's work; never retain tenant in the pool."""
    if (
        not isinstance(tenant_id, str)
        or not tenant_id.strip()
        or "\x00" in tenant_id
        or len(tenant_id) > 256
    ):
        raise ConfigurationError("Authenticated tenant context is required")
    require_postgres(engine)
    with engine.begin() as connection:
        if connection.connection.driver_connection.autocommit:
            raise ConfigurationError("Tenant transactions require autocommit disabled")
        previous = connection.execute(
            text("SELECT nullif(current_setting('sentinel.tenant_id', true), '')")
        ).scalar_one()
        if previous is not None:
            # A session-scoped setting would be restored after SET LOCAL ends.
            connection.invalidate()
            raise ConfigurationError("Pooled connection contained session-scoped tenant context")
        connection.execute(
            text("SELECT set_config('sentinel.tenant_id', :tenant, true)"), {"tenant": tenant_id}
        )
        yield connection


def apply_tenant_policy(connection: Connection, service: ServiceSchema, table: str) -> None:
    """Migration pattern for tables with a non-null tenant_id and composite tenant keys."""
    table = identifier(table)
    qualified = f'"{service.schema}"."{table}"'
    predicate = "tenant_id = nullif(pg_catalog.current_setting('sentinel.tenant_id', true), '')"
    connection.exec_driver_sql(f"ALTER TABLE {qualified} ENABLE ROW LEVEL SECURITY")
    connection.exec_driver_sql(f"ALTER TABLE {qualified} FORCE ROW LEVEL SECURITY")
    connection.exec_driver_sql(
        f"CREATE POLICY tenant_scope ON {qualified} USING ({predicate}) WITH CHECK ({predicate})"
    )
    connection.exec_driver_sql(f"REVOKE ALL ON {qualified} FROM PUBLIC")
    connection.exec_driver_sql(
        f'GRANT SELECT, INSERT, UPDATE, DELETE ON {qualified} TO "{service.runtime_role}"'
    )
