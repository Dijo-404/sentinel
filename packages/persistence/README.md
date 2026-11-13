# SN-003 — Tenant persistence toolkit

Optional `persistence-kit.v1` SQLAlchemy/psycopg helpers with an Alembic demonstration and real PostgreSQL acceptance checks. Services keep their own schemas, credentials, migrations and dependency installations. This package creates only synthetic `demo_records` and `demo_notes`; it owns no financial tables.

**Owned root:** `packages/persistence/` · **Branch:** `feat/sn-003-persistence`

Contract: `sentinel.task-contracts.v1`, SHA-256 `0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb`. The [typed snapshot](src/sentinel_persistence/contracts.py), [library/CLI contract](contracts/persistence-kit.v1.json) and [synthetic examples](fixtures/demo.json) are local; no sibling package or validator is needed.

## Standalone setup and checks

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), GNU Make and a working Docker daemon with permission to run containers. The first run needs package/image downloads. From this directory:

```sh
make setup
make check
```

Or from the repository root:

```sh
make -C packages/persistence check
make check
```

`uv sync --frozen` installs only this module's locked dependencies. The module check runs Ruff lint/format checks and all tests. PostgreSQL checks are mandatory: unavailable Docker/PostgreSQL is a failing check, never a skipped test or an in-memory substitute.

Each test session creates a new PostgreSQL 17 Alpine container, a randomly named `sentinel_demo_*` database, random administrative password and separate owner/runtime login roles per service. It publishes only a random **127.0.0.1** port, uses tmpfs storage, and removes its own container in `finally`. It never consumes `DATABASE_URL` or an existing Sentinel service. The image is pinned in [tests/conftest.py](tests/conftest.py) to digest `d3244e8ce3f165ee3c93d9c4a4b1d0fe48b3a89e2287b717fdcbbde92d405065`. A process killed before cleanup may leave a container named `sentinel-sn003-*`; inspect and remove only that specific test container.

To exercise the CLI's complete migrate → seed → runtime inspect → reset journey in its own disposable database:

```sh
uv run --frozen pytest tests/test_cli.py::test_cli_real_database_roundtrip
```

## Public patterns

```python
from sqlalchemy import create_engine, text
from sentinel_persistence import tenant_transaction

runtime_engine = create_engine(runtime_database_url, hide_parameters=True)
# This value comes from authenticated server context, never a request/model field.
with tenant_transaction(runtime_engine, authenticated_tenant_id) as connection:
    records = connection.execute(
        text("SELECT id FROM my_service.records WHERE tenant_id=:tenant"),
        {"tenant": authenticated_tenant_id},
    ).all()
```

`tenant_transaction` owns one transaction, validates nonempty opaque tenant IDs, sets `sentinel.tenant_id` with transaction-local `set_config(..., true)`, and commits or rolls back on exit. Tenant context disappears after either outcome. A contaminated pool connection with session-scoped tenant context is invalidated and rejected. Autocommit engines are rejected. This synchronous helper supports the psycopg driver declared by this package; it does not introduce an ORM repository or async session framework.

[The bundled migration](src/sentinel_persistence/migrations/versions/0001_demo_notes.py) is a copyable, non-financial example:

- Primary key `(tenant_id, id)` permits the same ID in different tenants.
- Foreign key `(tenant_id, record_id)` references `(tenant_id, id)` in the same schema, so an ID from another tenant cannot satisfy it.
- `apply_tenant_policy(connection, ServiceSchema(...), table)` enables and **forces** RLS, sets both `USING` and `WITH CHECK`, revokes public table privileges and grants only SELECT/INSERT/UPDATE/DELETE to the runtime role. The predicate denies rows when tenant context is missing or empty.
- Migrations qualify every object and use a schema-local `alembic_version`. They never change `search_path`, migrate a sibling schema or grant runtime access to migration history.

A service may reuse the helpers or implement these patterns locally. It must own its production table definitions and Alembic chain; it must **not** run this demonstration as a shared migration service. Keep model imports and SQLAlchemy in adapters/composition, outside framework-free business code.

## Isolated schema and role provisioning

The tests model independent `demo_intake_*` and `demo_workflow_*` services. For a separately provisioned disposable local database, the equivalent administrative setup is below. Replace passwords locally and repeat with distinct names for a sibling service; do not grant memberships between service roles.

```sql
-- Only in a new disposable database called sentinel_demo_local.
REVOKE ALL ON DATABASE sentinel_demo_local FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE ROLE demo_intake_owner LOGIN PASSWORD 'REPLACE_LOCALLY'
  NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT;
CREATE ROLE demo_intake_runtime LOGIN PASSWORD 'REPLACE_LOCALLY'
  NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT;
GRANT CONNECT ON DATABASE sentinel_demo_local TO demo_intake_owner, demo_intake_runtime;
CREATE SCHEMA demo_intake AUTHORIZATION demo_intake_owner;
```

The schema owner runs migrations. Runtime credentials cannot create tables/schemas, disable RLS, truncate, edit migration state, assume the owner/sibling role, or read the sibling schema. `migrate_demo` verifies ownership and rejects runtime roles with privileged attributes, membership in the schema owner or a privileged role, or schema CREATE permission. Deployment provisioning must also revoke inherited/public/cross-service grants and database CREATE/TEMP permissions. A privileged administrator and table owner can alter security policy; runtime identities must have neither authority.

RLS is defense in depth. A runtime login can set a custom PostgreSQL setting, so SQL access must stay inside trusted server code with parameterized statements and authenticated tenant/subject authorization. This kit does not authenticate principals, authorize customer subjects/cases, or prevent arbitrary SQL executed with stolen runtime credentials. Application queries still explicitly scope tenants.

## CLI configuration and preview

[.env.example](.env.example) describes all variables. Environment files are documentation only; export values locally through your shell/secret manager. `DATABASE_URL` is secret server-side configuration and must use `postgresql+psycopg://.../database`. The other fields select the service schema, runtime role, sandbox environment, expected contract and server-authenticated tenant (synthetic in this demo).

With the disposable database and roles provisioned above, export `PERSISTENCE_SCHEMA=demo_intake`, `PERSISTENCE_RUNTIME_ROLE=demo_intake_runtime`, `PERSISTENCE_ENVIRONMENT=sandbox`, and `PERSISTENCE_TENANT_ID=demo-tenant-a`. Set `DATABASE_URL` to the appropriate local identity for each operation:

| Command | Database identity | Behavior |
| --- | --- | --- |
| `uv run --frozen sentinel-persistence migrate` | Schema owner | Upgrade this schema's bundled demo Alembic chain; repeat is a no-op. |
| `uv run --frozen sentinel-persistence seed` | Disposable sandbox administrator with all-row visibility | Insert exactly two synthetic records and two related notes; repeat is a no-op. |
| `make preview` | Runtime login | Emit a JSON report of a real tenant-scoped read and supported demo migration. |
| `uv run --frozen sentinel-persistence reset` | Disposable sandbox administrator with all-row visibility | Delete only the validated fixture set in this schema; retain schema/migration state. |

`python -m sentinel_persistence` exposes the same operations. Exit 0 means the requested database operation succeeded; exit 2 means unsafe/missing/incompatible configuration; exit 1 means a database failure. Errors suppress credentials, raw SQL and record values. There is no fixture fallback. Example report:

```json
{"contract_version":"sentinel.task-contracts.v1","evidence_mode":"real-postgresql/synthetic-records","migration_revision":"0001_demo_notes","port":"persistence-kit.v1","schema":"demo_intake","tenant_records":1}
```

Every mutating demo helper requires **all three** guards: environment exactly `sandbox`, schema starting `demo_`, database starting `sentinel_demo_`. Seed/reset acquire exclusive transactional locks and inspect every tenant with `row_security=off`; this requires sandbox administrative all-row visibility and fails for ordinary runtime/forced-owner credentials. Unknown tenants, extra IDs and altered record/note contents are refused without mutation. A naming guard alone is not an environment credential boundary: supply only disposable sandbox credentials.

The library-only `migrate_demo(..., revision="base", environment="sandbox")` drops the two demonstration tables; use it only to test rollback in disposable databases. Before dropping, the schema owner takes exclusive locks and temporarily removes FORCE for its own all-row fixture validation, while runtime RLS remains enabled and runtime access is blocked by locks. Unknown data aborts and rolls back both data and RLS changes. Re-upgrade starts an empty demo schema. Service migrations and backups need their own rollout/restore decisions.

## Compatibility checklist and evidence

- [x] Task-local typed contract and examples; exact pinned version/hash recorded.
- [x] Real SQLAlchemy/psycopg adapter exercised against private PostgreSQL with actual login roles.
- [x] Upgrade/repeat/downgrade/re-upgrade; separate schema histories and sibling data preserved.
- [x] Composite keys/FKs, same IDs in different tenants, forced-owner RLS, denied cross-tenant writes/read visibility.
- [x] Missing tenant, autocommit, pool contamination, transaction commit/rollback, denied DDL/TRUNCATE/role escalation/sibling reads.
- [x] Sandbox/fixture-only mutation guards, rejected downgrade leaves data and FORCE RLS intact.
- [x] CLI roundtrip, required-version mismatch, malformed configuration, database outage and redacted errors.
- [ ] Integration with independently versioned Sentinel services, production identity/subject authorization, async sessions, other PostgreSQL versions, PgBouncer and operational backup/restore.

Observed on 13 November 2026: Python 3.13.18, uv 0.13.7, Docker 29.9.3, pinned PostgreSQL 17 image; `make check` passes lint, formatting and 34 tests. Root `make check` passes metadata validation and 19 repository tests. The same 34 tests pass from an owned-directory-only copy under `/tmp`, including a non-editable wheel installation imported from `site-packages`; no repository root or sibling sources are present.

Evidence is the real toolkit and real PostgreSQL with synthetic records, standalone. No peer stubs, running sibling services, payment simulator/provider, model/voice calls or external credentials are involved. These checks do not establish product assembly, financial execution safety, customer credit, pilot or release readiness.

References: [PostgreSQL RLS](https://www.postgresql.org/docs/17/ddl-rowsecurity.html), [transaction-local settings](https://www.postgresql.org/docs/17/functions-admin.html#FUNCTIONS-ADMIN-SET), [SQLAlchemy transactions](https://docs.sqlalchemy.org/en/20/core/connections.html#connect-and-begin-once-from-the-engine), [Alembic connection sharing and schema recipes](https://alembic.sqlalchemy.org/en/latest/cookbook.html).
