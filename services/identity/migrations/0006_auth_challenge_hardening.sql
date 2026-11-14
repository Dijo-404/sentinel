-- Harden challenges for DBs that applied the pre-hardening 0005 shape.
ALTER TABLE identity.auth_challenges
    ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0;

ALTER TABLE identity.auth_delivery_log
    DROP COLUMN IF EXISTS raw_code;
