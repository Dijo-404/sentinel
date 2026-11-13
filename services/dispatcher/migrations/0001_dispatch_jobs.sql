-- Dispatcher-owned durable worker bookkeeping only.
-- Does not store reservations, approvals, balances, or provider ledger authority.
CREATE TABLE IF NOT EXISTS dispatcher.dispatch_jobs (
    tenant_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    provider_ref TEXT NOT NULL,
    lease_id TEXT NOT NULL,
    action_digest TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    phase TEXT NOT NULL,
    same_key_retry BOOLEAN NOT NULL,
    status_lookup BOOLEAN NOT NULL,
    provider_status TEXT,
    outcome_status TEXT,
    reason_code TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, action_id),
    UNIQUE (tenant_id, provider_ref)
);
