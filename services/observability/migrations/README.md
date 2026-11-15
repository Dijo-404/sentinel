# observability schema

Owned schema: `observability`.

When `OBSERVABILITY_DATABASE_URL` is set, `PostgresSignalStore.migrate()` creates:

| Table     | Purpose                                          |
| --------- | ------------------------------------------------ |
| `signals` | Persisted telemetry signals keyed by `signal_id` |

Apply via serve/bootstrap (auto-migrate on app build) or `make seed`.
No Alembic; SQLAlchemy metadata + `CREATE SCHEMA IF NOT EXISTS`.
