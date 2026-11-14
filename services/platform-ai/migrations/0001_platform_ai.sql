-- platform-ai.v1: admin AI config + run metadata (no money columns).
CREATE SCHEMA IF NOT EXISTS platform_ai;

CREATE TABLE IF NOT EXISTS platform_ai.ai_configs (
    tenant_id TEXT PRIMARY KEY,
    models JSONB NOT NULL,
    kill_switch BOOLEAN NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS platform_ai.ai_runs (
    run_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ai_runs_tenant_started_idx
    ON platform_ai.ai_runs (tenant_id, started_at DESC);
