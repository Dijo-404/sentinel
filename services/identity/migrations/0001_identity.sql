-- Identity-owned schema (SN-035). No money/ledger tables.
CREATE SCHEMA IF NOT EXISTS identity;

CREATE TABLE IF NOT EXISTS identity.users (
    user_id uuid PRIMARY KEY,
    account_type text NOT NULL CHECK (account_type IN ('customer', 'staff')),
    email text NOT NULL UNIQUE,
    display_name text NOT NULL,
    status text NOT NULL CHECK (status IN ('pending', 'active', 'suspended', 'deactivated')),
    authz_version bigint NOT NULL DEFAULT 1 CHECK (authz_version >= 1),
    password_hash text NOT NULL,
    tenant_id text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS identity.role_assignments (
    assignment_id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES identity.users(user_id),
    tenant_id text NOT NULL,
    role_id text NOT NULL,
    scope_key text NOT NULL,
    merchant_ref text,
    team_id text,
    status text NOT NULL CHECK (status IN ('pending', 'active', 'revoked')),
    granted_by uuid REFERENCES identity.users(user_id),
    granted_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    grant_review_id uuid
);

CREATE UNIQUE INDEX IF NOT EXISTS one_active_role_scope
ON identity.role_assignments (user_id, tenant_id, role_id, scope_key)
WHERE status = 'active';

CREATE TABLE IF NOT EXISTS identity.sessions (
    session_id uuid PRIMARY KEY,
    token_hash text NOT NULL UNIQUE,
    user_id uuid NOT NULL REFERENCES identity.users(user_id),
    assignment_id uuid REFERENCES identity.role_assignments(assignment_id),
    authz_version bigint NOT NULL,
    mfa_verified_at timestamptz,
    issued_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK (expires_at > issued_at)
);

CREATE TABLE IF NOT EXISTS identity.staff_invitations (
    invitation_id uuid PRIMARY KEY,
    work_email text NOT NULL,
    display_name text NOT NULL,
    tenant_id text NOT NULL,
    role_id text NOT NULL,
    scope_key text NOT NULL,
    token_hash text NOT NULL UNIQUE,
    status text NOT NULL CHECK (status IN ('pending', 'accepted', 'revoked', 'expired')),
    review_state text NOT NULL DEFAULT 'not_required'
        CHECK (review_state IN ('not_required', 'awaiting_review', 'approved', 'rejected')),
    privileged_change_id uuid,
    invited_by uuid NOT NULL REFERENCES identity.users(user_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    idempotency_key text NOT NULL UNIQUE,
    merchant_ref text,
    team_id text,
    reason text,
    accepted_at timestamptz,
    revoked_at timestamptz,
    accepted_user_id uuid REFERENCES identity.users(user_id)
);

CREATE TABLE IF NOT EXISTS identity.privileged_change_requests (
    change_id uuid PRIMARY KEY,
    kind text NOT NULL CHECK (kind IN ('invite', 'grant')),
    state text NOT NULL CHECK (state IN ('pending', 'approved', 'rejected')),
    maker_user_id uuid NOT NULL REFERENCES identity.users(user_id),
    reviewer_user_id uuid REFERENCES identity.users(user_id),
    role_id text NOT NULL,
    tenant_id text NOT NULL,
    target_user_id uuid REFERENCES identity.users(user_id),
    invitation_id uuid,
    assignment_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    decided_at timestamptz,
    reason text,
    decision_reason text
);

CREATE TABLE IF NOT EXISTS identity.identity_audit_events (
    event_id uuid PRIMARY KEY,
    actor_user_id uuid,
    action text NOT NULL,
    target_type text NOT NULL,
    target_id text NOT NULL,
    tenant_id text,
    at timestamptz NOT NULL DEFAULT now(),
    details_json text NOT NULL DEFAULT '{}',
    request_id text NOT NULL DEFAULT 'request-local'
);
