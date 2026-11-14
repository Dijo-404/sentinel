# evaluation migrations

Apply `0001_evaluation_reports.sql` against `EVALUATION_DATABASE_URL`, or let
`PostgresReportStore.migrate()` / `sentinel-evaluation seed` create the schema
and table via SQLAlchemy (`checkfirst=True`).

Schema: `evaluation.run_reports (run_id TEXT PK, payload JSONB)`.
