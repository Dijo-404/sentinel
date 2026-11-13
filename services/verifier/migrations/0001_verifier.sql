-- Verifier-owned durable inbox, rechecks, assessments, and provider bindings.
-- Never stores ledger reservations, approvals, balances, or competing financial authority.
CREATE SCHEMA IF NOT EXISTS verifier;

CREATE TABLE IF NOT EXISTS verifier.webhook_inbox (
    tenant_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'simulator',
    provider_ref TEXT NOT NULL,
    event_type TEXT NOT NULL,
    merchant_ref TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload_json TEXT NOT NULL,
    signature_hex TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ,
    process_status TEXT NOT NULL DEFAULT 'ACCEPTED',
    reason_code TEXT,
    PRIMARY KEY (tenant_id, event_id)
);

CREATE TABLE IF NOT EXISTS verifier.recheck_jobs (
    tenant_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    case_id TEXT NOT NULL,
    case_revision INT NOT NULL,
    action_id TEXT NOT NULL,
    provider_ref TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    lease_expires_at TIMESTAMPTZ,
    attempts INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, job_id),
    UNIQUE (tenant_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS verifier.assessments (
    tenant_id TEXT NOT NULL,
    assessment_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    case_revision INT NOT NULL,
    action_id TEXT NOT NULL,
    provider_ref TEXT NOT NULL,
    assessed_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL,
    PRIMARY KEY (tenant_id, assessment_id)
);

CREATE TABLE IF NOT EXISTS verifier.provider_bindings (
    tenant_id TEXT NOT NULL,
    provider_ref TEXT NOT NULL,
    action_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    case_revision INT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, provider_ref)
);
