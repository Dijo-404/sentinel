-- Durable invitation delivery outbox + sandbox inbox projection (SN-035 finding #11).
-- Plaintext tokens live only here for local/sandbox delivery; never returned by admin invite API.

CREATE TABLE IF NOT EXISTS identity.invitation_delivery_outbox (
    delivery_id uuid PRIMARY KEY,
    invitation_id uuid NOT NULL REFERENCES identity.staff_invitations(invitation_id),
    work_email text NOT NULL,
    raw_token text NOT NULL,
    status text NOT NULL CHECK (status IN ('pending', 'delivered')),
    created_at timestamptz NOT NULL DEFAULT now(),
    delivered_at timestamptz,
    acceptance_link text,
    UNIQUE (invitation_id)
);

CREATE INDEX IF NOT EXISTS invitation_delivery_pending_idx
ON identity.invitation_delivery_outbox (status)
WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS invitation_delivery_inbox_email_idx
ON identity.invitation_delivery_outbox (work_email, delivered_at DESC)
WHERE status = 'delivered';
