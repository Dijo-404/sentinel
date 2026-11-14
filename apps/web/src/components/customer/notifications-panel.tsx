"use client";

import { useActionState, useEffect, useState } from "react";
import type { IdentityNotification } from "../../../tests/stubs/identity";
import {
  markNotificationReadAction,
  type MarkReadActionResult,
} from "@/lib/server/customer-actions";

type Props = {
  notifications?: IdentityNotification[];
  error?: { code: string; message: string } | null;
};

const initial: MarkReadActionResult | null = null;

/**
 * Customer Notifications: identity GET /v1/auth/notifications + mark-read.
 * Real-peer failure stays visible — never “Not available yet”.
 */
export function NotificationsPanel({ notifications, error }: Props) {
  const [rows, setRows] = useState<IdentityNotification[]>(
    notifications ?? [],
  );
  const [state, action, pending] = useActionState(
    markNotificationReadAction,
    initial,
  );

  useEffect(() => {
    setRows(notifications ?? []);
  }, [notifications]);

  useEffect(() => {
    if (!state || !state.ok) return;
    setRows((prev) =>
      prev.map((n) =>
        n.notification_id === state.notification_id
          ? { ...n, read_at: state.read_at }
          : n,
      ),
    );
  }, [state]);

  const loadPeerError = Boolean(error);
  const actionPeerError = Boolean(state && !state.ok && state.peerError);
  const peerError = loadPeerError || actionPeerError;
  const peerMessage = loadPeerError
    ? error!.message
    : state && !state.ok && state.peerError
      ? state.message
      : null;

  if (loadPeerError) {
    return (
      <div className="panel stack" data-testid="customer-notifications">
        <h1>Notifications</h1>
        <div
          className="state-banner"
          data-tone="error"
          data-testid="peer-error"
          role="alert"
        >
          <strong>Identity unavailable</strong>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            {peerMessage}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="panel stack" data-testid="customer-notifications">
      <h1>Notifications</h1>
      <p className="muted">
        Inbox from identity <code>GET /v1/auth/notifications</code>.
      </p>

      {actionPeerError ? (
        <div
          className="state-banner"
          data-tone="error"
          data-testid="peer-error"
          role="alert"
        >
          <strong>Identity unavailable</strong>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            {peerMessage}
          </p>
        </div>
      ) : null}

      {rows.length === 0 ? (
        <div
          className="state-banner"
          data-tone="empty"
          data-testid="state-empty"
          role="status"
        >
          <strong>No notifications</strong>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            Your inbox is empty.
          </p>
        </div>
      ) : (
        <ul className="stack" data-testid="customer-notifications-list">
          {rows.map((n) => (
            <li key={n.notification_id} className="stack">
              <strong>{n.title}</strong>
              <p style={{ margin: 0 }}>{n.body}</p>
              <p className="muted" style={{ margin: 0 }}>
                {n.created_at}
              </p>
              {n.read_at ? (
                <p
                  className="muted"
                  data-testid={`notification-${n.notification_id}-read`}
                  style={{ margin: 0 }}
                >
                  Read {n.read_at}
                </p>
              ) : (
                <form action={action}>
                  <input
                    type="hidden"
                    name="notification_id"
                    value={n.notification_id}
                  />
                  <button
                    type="submit"
                    disabled={pending}
                    data-testid={`mark-read-${n.notification_id}`}
                  >
                    {pending ? "Marking…" : "Mark read"}
                  </button>
                </form>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
