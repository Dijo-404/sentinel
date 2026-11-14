# merchant-analytics schema

Owned schema: `merchant_analytics`.

When `MERCHANT_ANALYTICS_DATABASE_URL` is set, `PostgresMetricsSnapshotStore.migrate()`
creates:

| Table | Purpose |
| --- | --- |
| `merchant_metrics_snapshots` | Persisted `MerchantMetrics` keyed by tenant, merchant_ref, window |

Apply via serve/bootstrap (auto-migrate on app build) or `make seed`.
No Alembic; SQLAlchemy metadata + `CREATE SCHEMA IF NOT EXISTS`.
