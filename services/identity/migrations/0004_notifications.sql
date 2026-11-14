-- Per-user inbox for customer/staff notifications (Wave 3).
CREATE TABLE IF NOT EXISTS identity.notifications (
    notification_id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES identity.users(user_id),
    title text NOT NULL,
    body text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    read_at timestamptz
);

CREATE INDEX IF NOT EXISTS notifications_user_created_idx
ON identity.notifications (user_id, created_at DESC);
