"use client";

import { useActionState, useMemo } from "react";
import {
  toPublicProfileUser,
  type PublicProfileUser,
} from "@/lib/identity-public";
import {
  patchProfileAction,
  type ProfileActionResult,
} from "@/lib/server/customer-actions";

type Props = {
  user?: PublicProfileUser | null;
  error?: { code: string; message: string } | null;
};

const initial: ProfileActionResult | null = null;

/**
 * Customer Profile: identity GET/PATCH /v1/auth/me.
 * Real-peer failure stays visible — never “Not available yet”.
 * Accepts public profile fields only (no password).
 */
export function ProfilePanel({ user, error }: Props) {
  const [state, action, pending] = useActionState(patchProfileAction, initial);

  const loadPeerError = Boolean(error);
  const savePeerError = Boolean(state && !state.ok && state.peerError);
  const peerError = loadPeerError || savePeerError;
  const peerMessage = loadPeerError
    ? error!.message
    : state && !state.ok && state.peerError
      ? state.message
      : null;
  const softError =
    state && !state.ok && !state.peerError ? state.message : null;
  const success = Boolean(state && state.ok);

  const displayUser = useMemo((): PublicProfileUser | null => {
    if (state && state.ok) return toPublicProfileUser(state.user);
    if (user && !loadPeerError) return toPublicProfileUser(user);
    return null;
  }, [state, user, loadPeerError]);

  return (
    <div className="panel stack" data-testid="customer-profile">
      <h1>Profile</h1>
      <p className="muted">
        Account details from identity <code>GET /v1/auth/me</code>. Updates use{" "}
        <code>PATCH /v1/auth/me</code> (display name and language only).
      </p>

      {peerError ? (
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

      {displayUser ? (
        <>
          {success && !savePeerError ? (
            <div
              className="state-banner"
              data-tone="empty"
              data-testid="profile-success"
              role="status"
            >
              <p>{state && state.ok ? state.message : null}</p>
            </div>
          ) : null}

          <form
            action={action}
            className="stack"
            data-testid="customer-profile-data"
          >
            <div>
              <p className="muted" style={{ margin: 0 }}>
                Email
              </p>
              <p style={{ margin: 0 }}>{displayUser.email}</p>
            </div>
            <label>
              Display name
              <input
                name="display_name"
                type="text"
                required
                defaultValue={displayUser.display_name}
                data-testid="profile-display-name"
              />
            </label>
            <label>
              Preferred language
              <input
                name="preferred_language"
                type="text"
                defaultValue={displayUser.preferred_language ?? ""}
                data-testid="profile-language"
              />
            </label>
            {softError ? (
              <div
                className="state-banner"
                data-tone="error"
                data-testid="profile-error"
                role="alert"
              >
                <p>{softError}</p>
              </div>
            ) : null}
            <button
              type="submit"
              disabled={pending}
              data-testid="profile-save"
            >
              {pending ? "Saving…" : "Save profile"}
            </button>
          </form>
        </>
      ) : null}
    </div>
  );
}
