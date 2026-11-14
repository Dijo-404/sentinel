"use client";

import { useActionState } from "react";
import {
  confirmVerifyAction,
  requestVerifyAction,
  type ChallengeActionResult,
} from "@/lib/server/auth-actions";

const initial: ChallengeActionResult | null = null;

export function VerifyContactForm() {
  const [requestState, requestAction, requestPending] = useActionState(
    requestVerifyAction,
    initial,
  );
  const [confirmState, confirmAction, confirmPending] = useActionState(
    confirmVerifyAction,
    initial,
  );

  const peerError =
    (requestState && !requestState.ok && requestState.peerError) ||
    (confirmState && !confirmState.ok && confirmState.peerError);
  const peerMessage =
    requestState && !requestState.ok && requestState.peerError
      ? requestState.message
      : confirmState && !confirmState.ok && confirmState.peerError
        ? confirmState.message
        : null;
  const success =
    (requestState && requestState.ok) || (confirmState && confirmState.ok);

  return (
    <div className="auth-card panel stack" data-testid="auth-verify">
      <div>
        <p className="brand auth-brand">Sentinel</p>
        <h1>Verify contact</h1>
        <p className="muted">
          Request a sandbox verification code, then confirm it.
        </p>
      </div>

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

      {success && !peerError ? (
        <div
          className="state-banner"
          data-tone="empty"
          data-testid="verify-success"
          role="status"
        >
          <p>
            {confirmState && confirmState.ok
              ? confirmState.message
              : requestState && requestState.ok
                ? requestState.message
                : null}
          </p>
          {requestState && requestState.ok && requestState.sandbox_code ? (
            <p className="muted" data-testid="verify-sandbox-code">
              Sandbox code: {requestState.sandbox_code}
            </p>
          ) : null}
        </div>
      ) : null}

      {!peerError ? (
        <>
          <form action={requestAction} className="stack">
            <button
              type="submit"
              disabled={requestPending}
              data-testid="verify-request"
            >
              {requestPending ? "Requesting…" : "Send verification code"}
            </button>
          </form>

          <form action={confirmAction} className="stack">
            <label>
              Verification code
              <input
                name="code"
                type="text"
                required
                autoComplete="one-time-code"
                data-testid="verify-code"
              />
            </label>
            {confirmState && !confirmState.ok && !confirmState.peerError ? (
              <div
                className="state-banner"
                data-tone="error"
                data-testid="verify-error"
                role="alert"
              >
                <p>{confirmState.message}</p>
              </div>
            ) : null}
            <button
              type="submit"
              disabled={confirmPending}
              data-testid="verify-confirm"
            >
              {confirmPending ? "Confirming…" : "Confirm"}
            </button>
          </form>
        </>
      ) : null}
    </div>
  );
}
