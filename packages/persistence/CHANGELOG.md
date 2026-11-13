# SN-003 changelog

## Unreleased

### Added — 13 November 2026

- Installable optional `persistence-kit.v1` package with local manifest/lockfile, environment example, setup/check/preview targets, typed contract snapshot and synthetic compatibility examples.
- SQLAlchemy/psycopg tenant transactions with validated authenticated context, transaction-local settings, commit/rollback cleanup, rejection of autocommit and invalidation of contaminated pooled connections.
- Schema-local Alembic example using composite tenant primary/foreign keys, forced RLS and distinct owner/runtime roles. No financial state or cross-service migration chain.
- Guarded, idempotent synthetic seed/reset utilities and fixture-only downgrade validation under exclusive transactional locks. Mutations refuse non-sandbox namespaces and non-fixture data.
- Redacted CLI migrate/seed/inspect/reset operations with explicit unavailable/incompatible database failures and no fixture fallback.
- Real PostgreSQL 17 checks using a pinned, loopback-only disposable Docker database, random credentials, actual unprivileged login roles and cleanup; no sibling dependencies.

### Validation and limits

- `make check`: Ruff lint/format and 34 tests pass against real PostgreSQL and synthetic records, including CLI lifecycle, schema/role/RLS isolation, composite keys, pool cleanup, guarded seed/reset/downgrade and failure/redaction boundaries.
- Owned-directory-only copy: the same lint/format and 34 tests pass; a non-editable wheel installation also passes all 34 tests with bundled migrations loaded from `site-packages`.
- Root `make check`: repository metadata validation and 19 repository tests pass; this is separate from database acceptance.
- Contract baseline: `sentinel.task-contracts.v1`, SHA-256 `0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa`.
- Checks need Python 3.11+, uv, Make and Docker/image access; no external provider credentials. Tested with Python 3.13.18/PostgreSQL 17; async sessions, other database versions, PgBouncer, real-service assembly and operational restore are unverified. RLS supplements trusted server authentication and subject-scoped authorization.
