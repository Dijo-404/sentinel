# Risk schema migrations

Optional PostgreSQL persistence is owned by this module.

When `RISK_DATABASE_URL` is set, `PostgresRiskStore.migrate()` creates schema `risk` and tables:

- `risk_investigations`
- `risk_findings`
- `risk_restrictions`

Fixture mode uses `MemoryRiskStore` and does not require PostgreSQL. Real-peers mode refuses the default memory store unless a durable store is injected.
