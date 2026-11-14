-- Reference DDL for module-owned tables (also applied via SQLAlchemy metadata).
CREATE SCHEMA IF NOT EXISTS workflow;

CREATE TABLE IF NOT EXISTS workflow.jobs (
  job_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  job_key TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_digest TEXT NOT NULL,
  thread_id TEXT NOT NULL,
  status TEXT NOT NULL,
  detail TEXT,
  created_at TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, job_key)
);

CREATE TABLE IF NOT EXISTS workflow.result_outbox (
  outbox_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  event_key TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  available_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, case_id, event_key)
);

CREATE TABLE IF NOT EXISTS workflow.decisions (
  thread_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  approval_json TEXT NOT NULL,
  principal_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);
