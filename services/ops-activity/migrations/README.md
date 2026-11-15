# ops-activity schema

Owned schema: `ops_activity`.

When `OPS_ACTIVITY_DATABASE_URL` is set, `PostgresActivityStore.migrate()` creates:

| Table            | Purpose                                             |
| ---------------- | --------------------------------------------------- |
| `activity_items` | Persisted activity feed rows keyed by `activity_id` |

Apply via serve/bootstrap (auto-migrate on app build) or `make seed`.
No Alembic; SQLAlchemy metadata + `CREATE SCHEMA IF NOT EXISTS`.
