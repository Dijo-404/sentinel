-- merchant-teams.v1 Postgres schema (MERCHANT_TEAMS_DATABASE_URL).
-- Applied by PostgresStaffStore.migrate(); this file is owned documentation.

CREATE SCHEMA IF NOT EXISTS merchant_teams;

CREATE TABLE IF NOT EXISTS merchant_teams.merchant_staff (
    staff_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    merchant_ref TEXT NOT NULL,
    display_name TEXT NOT NULL,
    roles_json JSONB NOT NULL,
    approval_limit_minor BIGINT NULL,
    currency TEXT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS ix_merchant_staff_tenant_merchant
    ON merchant_teams.merchant_staff (tenant_id, merchant_ref);

CREATE TABLE IF NOT EXISTS merchant_teams.staff_activity (
    event_id TEXT PRIMARY KEY,
    staff_id TEXT NOT NULL,
    at TEXT NOT NULL,
    kind TEXT NOT NULL,
    subject_ref TEXT NOT NULL,
    summary TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_staff_activity_staff_id
    ON merchant_teams.staff_activity (staff_id);

-- Append-only: no UPDATE/DELETE grants on staff_activity in deployed roles.
