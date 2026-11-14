-- Profile preferred_language for self-service PATCH /v1/auth/me.
ALTER TABLE identity.users
    ADD COLUMN IF NOT EXISTS preferred_language text NOT NULL DEFAULT '';
