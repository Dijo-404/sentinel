import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError

from sentinel_persistence import (
    ConfigurationError,
    ServiceSchema,
    inspect_demo,
    migrate_demo,
    reset_demo,
    seed_demo,
    tenant_transaction,
)


def spec(service):
    return ServiceSchema(service.schema, service.runtime_role)


def migrate(service, revision="head"):
    migrate_demo(service.owner, spec(service), environment="sandbox", revision=revision)


def rows(engine, schema):
    with engine.connect() as connection:
        return connection.execute(
            text(f'SELECT tenant_id, id, label FROM "{schema}".demo_records ORDER BY tenant_id, id')
        ).all()


@pytest.mark.parametrize(
    "schema, role",
    [
        ("public", "runtime"),
        ("pg_catalog", "runtime"),
        ("demo_ok; DROP SCHEMA x", "runtime"),
        ("demo_ok", "runtime; SELECT 1"),
        ("demo_ok", "demo_ok"),
        ("a" * 64, "runtime"),
    ],
)
def test_identifiers_reject_unsafe_or_shared_namespace(schema, role):
    with pytest.raises(ConfigurationError):
        ServiceSchema(schema, role)


@pytest.mark.parametrize("tenant", ["", " ", None, 12, "bad\x00tenant", "a" * 257])
def test_missing_or_malformed_authenticated_tenant_rejected(tenant, postgres):
    with pytest.raises(ConfigurationError):
        with tenant_transaction(postgres, tenant):
            pytest.fail("invalid tenant reached database work")


def test_migration_idempotency_schema_isolation_and_reversible_chain(services, postgres):
    with services("intake") as first, services("workflow") as sibling:
        migrate(first)
        migrate(sibling)
        seed_demo(postgres, spec(first), environment="sandbox")
        migrate(first)
        assert len(rows(postgres, first.schema)) == 2
        assert rows(postgres, sibling.schema) == []
        with first.owner.connect() as connection:
            assert (
                connection.execute(
                    text(f'SELECT version_num FROM "{first.schema}".alembic_version')
                ).scalar_one()
                == "0001_demo_notes"
            )
        migrate(first, "base")
        with postgres.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT to_regclass(:name)"), {"name": f"{first.schema}.demo_records"}
                ).scalar()
                is None
            )
        assert rows(postgres, sibling.schema) == []
        migrate(first)
        seed_demo(postgres, spec(first), environment="sandbox")
        assert len(rows(postgres, first.schema)) == 2


def test_seed_is_idempotent_and_reset_only_changes_owned_schema(services, postgres):
    with services("seed") as service, services("peer") as sibling:
        for item in (service, sibling):
            migrate(item)
            seed_demo(postgres, spec(item), environment="sandbox")
        seed_demo(postgres, spec(service), environment="sandbox")
        assert rows(postgres, service.schema) == [
            ("demo-tenant-a", "shared-record", "synthetic A"),
            ("demo-tenant-b", "shared-record", "synthetic B"),
        ]
        reset_demo(postgres, spec(service), environment="sandbox")
        assert rows(postgres, service.schema) == []
        assert len(rows(postgres, sibling.schema)) == 2


@pytest.mark.parametrize("operation", [migrate_demo, seed_demo, reset_demo])
def test_demo_mutation_refuses_non_sandbox_and_non_demo_schema(operation, services, postgres):
    with services("guard") as service:
        migrate(service)
        for environment, schema in [
            ("production", spec(service)),
            ("sandbox", ServiceSchema("service_data", service.runtime_role)),
        ]:
            with pytest.raises(ConfigurationError):
                operation(postgres, schema, environment=environment)
        assert rows(postgres, service.schema) == []


@pytest.mark.parametrize("operation", [seed_demo, reset_demo])
def test_demo_mutation_refuses_non_fixture_records_atomically(operation, services, postgres):
    with services("guard") as service:
        migrate(service)
        seed_demo(postgres, spec(service), environment="sandbox")
        with postgres.begin() as connection:
            connection.execute(
                text(
                    f'INSERT INTO "{service.schema}".demo_records VALUES '
                    "('other-tenant', 'private-record', 'non-demo')"
                )
            )
        before = rows(postgres, service.schema)
        with pytest.raises(ConfigurationError):
            operation(postgres, spec(service), environment="sandbox")
        assert rows(postgres, service.schema) == before


def test_rls_reads_and_writes_fail_closed_and_owner_is_forced(services, postgres):
    with services("rls") as service:
        migrate(service)
        seed_demo(postgres, spec(service), environment="sandbox")
        assert rows(service.runtime, service.schema) == []
        assert rows(service.owner, service.schema) == []
        with tenant_transaction(service.runtime, "demo-tenant-a") as connection:
            assert connection.execute(
                text(f'SELECT tenant_id, label FROM "{service.schema}".demo_records')
            ).all() == [("demo-tenant-a", "synthetic A")]
            assert (
                connection.execute(
                    text(
                        f'UPDATE "{service.schema}".demo_records '
                        "SET label='bad' WHERE tenant_id='demo-tenant-b'"
                    )
                ).rowcount
                == 0
            )
            assert (
                connection.execute(
                    text(
                        f'DELETE FROM "{service.schema}".demo_records '
                        "WHERE tenant_id='demo-tenant-b'"
                    )
                ).rowcount
                == 0
            )
        for tenant in (None, "demo-tenant-a"):
            with pytest.raises(DBAPIError) as failure:
                with service.runtime.begin() as connection:
                    if tenant:
                        connection.execute(
                            text("SELECT set_config('sentinel.tenant_id', :t, true)"), {"t": tenant}
                        )
                    connection.execute(
                        text(
                            f'INSERT INTO "{service.schema}".demo_records VALUES '
                            "('demo-tenant-b', 'forbidden', 'bad')"
                        )
                    )
            assert failure.value.orig.sqlstate == "42501"
        with pytest.raises(DBAPIError) as failure:
            with tenant_transaction(service.runtime, "demo-tenant-a") as connection:
                connection.execute(
                    text(f"UPDATE \"{service.schema}\".demo_records SET tenant_id='demo-tenant-b'")
                )
        assert failure.value.orig.sqlstate == "42501"


def test_composite_keys_allow_same_id_but_reject_cross_tenant_foreign_key(services, postgres):
    with services("keys") as service:
        migrate(service)
        seed_demo(postgres, spec(service), environment="sandbox")
        with tenant_transaction(service.runtime, "demo-tenant-b") as connection:
            connection.execute(
                text(
                    f'INSERT INTO "{service.schema}".demo_records VALUES '
                    "('demo-tenant-b', 'b-only', 'synthetic B extra')"
                )
            )
        with pytest.raises(IntegrityError) as failure:
            with tenant_transaction(service.runtime, "demo-tenant-a") as connection:
                connection.execute(
                    text(
                        f'INSERT INTO "{service.schema}".demo_notes VALUES '
                        "('demo-tenant-a', 'cross-tenant', 'b-only', 'bad')"
                    )
                )
        assert failure.value.orig.sqlstate == "23503"
        with pytest.raises(IntegrityError) as failure:
            with tenant_transaction(service.runtime, "demo-tenant-a") as connection:
                connection.execute(
                    text(
                        f'INSERT INTO "{service.schema}".demo_records VALUES '
                        "('demo-tenant-a', 'shared-record', 'duplicate')"
                    )
                )
        assert failure.value.orig.sqlstate == "23505"


def test_tenant_context_and_changes_do_not_leak_after_commit_or_rollback(services, postgres):
    with services("pool") as service:
        migrate(service)
        seed_demo(postgres, spec(service), environment="sandbox")
        with tenant_transaction(service.runtime, "demo-tenant-a") as connection:
            pid = connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
        assert rows(service.runtime, service.schema) == []
        with pytest.raises(RuntimeError, match="rollback"):
            with tenant_transaction(service.runtime, "demo-tenant-b") as connection:
                assert connection.execute(text("SELECT pg_backend_pid()")).scalar_one() == pid
                connection.execute(text(f'DELETE FROM "{service.schema}".demo_notes'))
                connection.execute(text(f'DELETE FROM "{service.schema}".demo_records'))
                raise RuntimeError("rollback")
        assert rows(service.runtime, service.schema) == []
        with tenant_transaction(service.runtime, "demo-tenant-b") as connection:
            assert (
                connection.execute(
                    text(f'SELECT count(*) FROM "{service.schema}".demo_records')
                ).scalar_one()
                == 1
            )


def test_runtime_login_denied_sibling_schema_ddl_role_escalation_and_migrations(services, postgres):
    with services("roles") as service, services("sibling") as sibling:
        migrate(service)
        migrate(sibling)
        with service.runtime.connect() as connection:
            assert connection.execute(text("SELECT session_user, current_user")).one() == (
                service.runtime_role,
                service.runtime_role,
            )
        for query in (
            f'SELECT * FROM "{sibling.schema}".demo_records',
            f'CREATE TABLE "{service.schema}".unauthorized (id integer)',
            f'SELECT * FROM "{service.schema}".alembic_version',
            f'ALTER TABLE "{service.schema}".demo_records DISABLE ROW LEVEL SECURITY',
            f'TRUNCATE "{service.schema}".demo_records',
            f'SET ROLE "{service.owner_role}"',
            f'SET ROLE "{sibling.runtime_role}"',
            "CREATE SCHEMA unauthorized",
            "CREATE TABLE public.unauthorized (id integer)",
        ):
            with pytest.raises(DBAPIError) as failure:
                with service.runtime.begin() as connection:
                    connection.execute(text(query))
            assert failure.value.orig.sqlstate == "42501"
        with pytest.raises(ConfigurationError):
            migrate_demo(service.runtime, spec(service), environment="sandbox")


def test_migration_rejects_privileged_runtime_and_role_membership(services, postgres):
    with services("unsafe") as service:
        for alteration in (
            f'ALTER ROLE "{service.runtime_role}" BYPASSRLS',
            f'GRANT "{service.owner_role}" TO "{service.runtime_role}"',
        ):
            with postgres.begin() as connection:
                connection.execute(text(alteration))
            with pytest.raises(ConfigurationError):
                migrate(service)
            with postgres.begin() as connection:
                connection.execute(text(f'ALTER ROLE "{service.runtime_role}" NOBYPASSRLS'))
                connection.execute(
                    text(f'REVOKE "{service.owner_role}" FROM "{service.runtime_role}"')
                )


def test_database_outage_never_falls_back_to_fixture(postgres):
    engine = create_engine(postgres.url.set(port=1), hide_parameters=True)
    try:
        with pytest.raises(OperationalError):
            with tenant_transaction(engine, "demo-tenant-a"):
                pytest.fail("unavailable database silently accepted")
    finally:
        engine.dispose()


def test_in_memory_database_cannot_replace_postgresql():
    engine = create_engine("sqlite://")
    try:
        with pytest.raises(ConfigurationError):
            with tenant_transaction(engine, "demo-tenant-a"):
                pytest.fail("PostgreSQL requirements cannot pass against in-memory storage")
    finally:
        engine.dispose()


def test_inspection_uses_real_runtime_and_rejects_incompatible_migration(services, postgres):
    with services("inspect") as service:
        migrate(service)
        seed_demo(postgres, spec(service), environment="sandbox")
        report = inspect_demo(service.runtime, spec(service), "demo-tenant-a")
        assert report.tenant_records == 1
        assert report.evidence_mode == "real-postgresql/synthetic-records"
        with postgres.begin() as connection:
            connection.exec_driver_sql(
                f"COMMENT ON TABLE \"{service.schema}\".demo_records IS 'incompatible-v2'"
            )
        with pytest.raises(ConfigurationError):
            inspect_demo(service.runtime, spec(service), "demo-tenant-a")


def test_session_context_contamination_rejected_and_connection_discarded(services, postgres):
    with services("dirty") as service:
        migrate(service)
        with service.runtime.begin() as connection:
            connection.execute(
                text("SELECT set_config('sentinel.tenant_id', 'wrong-tenant', false)")
            )
        with pytest.raises(ConfigurationError, match="session-scoped"):
            with tenant_transaction(service.runtime, "demo-tenant-a"):
                pytest.fail("session setting would leak into next pooled transaction")
        assert rows(service.runtime, service.schema) == []


def test_autocommit_rejected_instead_of_dropping_tenant_context(services):
    with services("autocommit") as service:
        engine = service.runtime.execution_options(isolation_level="AUTOCOMMIT")
        with pytest.raises(ConfigurationError, match="autocommit"):
            with tenant_transaction(engine, "demo-tenant-a"):
                pytest.fail("tenant context cannot span autocommitted statements")


def test_seed_with_runtime_login_fails_instead_of_hiding_non_demo_records(services, postgres):
    with services("seedrole") as service:
        migrate(service)
        with pytest.raises(DBAPIError):
            seed_demo(service.runtime, spec(service), environment="sandbox")
        assert rows(postgres, service.schema) == []


def test_downgrade_refuses_non_fixture_data_and_restores_forced_rls(services, postgres):
    with services("dropguard") as service:
        migrate(service)
        seed_demo(postgres, spec(service), environment="sandbox")
        with postgres.begin() as connection:
            connection.execute(
                text(
                    f'INSERT INTO "{service.schema}".demo_records VALUES '
                    "('non-demo', 'private', 'preserve me')"
                )
            )
        before = rows(postgres, service.schema)
        with pytest.raises(ConfigurationError):
            migrate(service, "base")
        assert rows(postgres, service.schema) == before
        assert rows(service.owner, service.schema) == []
