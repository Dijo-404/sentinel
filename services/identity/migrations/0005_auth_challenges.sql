-- Sandbox verify / MFA / password-reset challenges + loopback delivery log.
ALTER TABLE identity.users
    ADD COLUMN IF NOT EXISTS email_verified_at timestamptz;

CREATE TABLE IF NOT EXISTS identity.auth_challenges (
    challenge_id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES identity.users(user_id),
    challenge_type text NOT NULL
        CHECK (challenge_type IN ('email_verify', 'mfa', 'password_reset')),
    code_hash text NOT NULL,
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS auth_challenges_user_type_idx
ON identity.auth_challenges (user_id, challenge_type, created_at DESC);

CREATE TABLE IF NOT EXISTS identity.auth_delivery_log (
    log_id uuid PRIMARY KEY,
    channel text NOT NULL DEFAULT 'loopback',
    destination text NOT NULL,
    purpose text NOT NULL,
    challenge_id uuid NOT NULL REFERENCES identity.auth_challenges(challenge_id),
    user_id uuid NOT NULL REFERENCES identity.users(user_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    -- Sandbox peek only; never returned by public list/auth JSON by default.
    raw_code text NOT NULL
);

CREATE INDEX IF NOT EXISTS auth_delivery_log_user_purpose_idx
ON identity.auth_delivery_log (user_id, purpose, created_at DESC);
