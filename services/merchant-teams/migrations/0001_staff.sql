-- Optional local schema sketch for merchant-teams.v1.
-- Fixture checks use the in-memory store; this SQL is owned documentation only.

CREATE TABLE IF NOT EXISTS merchant_staff (
    staff_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    merchant_ref TEXT NOT NULL,
    display_name TEXT NOT NULL,
    roles_json TEXT NOT NULL,
    approval_limit_minor BIGINT NULL,
    currency TEXT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS staff_activity (
    event_id TEXT PRIMARY KEY,
    staff_id TEXT NOT NULL REFERENCES merchant_staff (staff_id),
    at TIMESTAMPTZ NOT NULL,
    kind TEXT NOT NULL,
    subject_ref TEXT NOT NULL,
    summary TEXT NOT NULL
);

-- Append-only: no UPDATE/DELETE grants on staff_activity in deployed roles.
