-- evaluation.v1: durable RunReport rows for HTTP serve/query.
CREATE SCHEMA IF NOT EXISTS evaluation;

CREATE TABLE IF NOT EXISTS evaluation.run_reports (
    run_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL
);
