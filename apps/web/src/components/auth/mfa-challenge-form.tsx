"use client";

import { useActionState } from "react";
import {
  mfaChallengeAction,
  mfaVerifyAction,
  type ChallengeActionResult,
} from "@/lib/server/auth-actions";

const initial: ChallengeActionResult | null = null;

export function MfaChallengeForm() {
  const [challengeState, challengeAction, challengePending] = useActionState(
    mfaChallengeAction,
    initial,
  );
  const [verifyState, verifyAction, verifyPending] = useActionState(mfaVerifyAction, initial);

  const peerError =
    (challengeState && !challengeState.ok && challengeState.peerError) ||
    (verifyState && !verifyState.ok && verifyState.peerError);
  const peerMessage =
    challengeState && !challengeState.ok && challengeState.peerError
      ? challengeState.message
      : verifyState && !verifyState.ok && verifyState.peerError
        ? verifyState.message
        : null;
  const challengeSoftError =
    challengeState && !challengeState.ok && !challengeState.peerError
      ? challengeState.message
      : null;
  const verifySoftError =
    verifyState && !verifyState.ok && !verifyState.peerError ? verifyState.message : null;
  const success = (challengeState && challengeState.ok) || (verifyState && verifyState.ok);

  return (
    <div className="auth-card panel stack" data-testid="auth-mfa">
      <div>
        <p className="brand auth-brand">Sentinel</p>
        <h1>Multi-factor authentication</h1>
        <p className="muted">Issue a sandbox MFA challenge, then enter the code.</p>
      </div>

      {peerError ? (
        <div className="state-banner" data-tone="error" data-testid="peer-error" role="alert">
          <strong>Identity unavailable</strong>
          <p className="muted" style={{ margin: "0.35rem 0 0" }}>
            {peerMessage}
          </p>
        </div>
      ) : null}

      {success && !peerError ? (
        <div className="state-banner" data-tone="empty" data-testid="mfa-success" role="status">
          <p>
            {verifyState && verifyState.ok
              ? verifyState.message
              : challengeState && challengeState.ok
                ? challengeState.message
                : null}
          </p>
          {challengeState && challengeState.ok && challengeState.sandbox_code ? (
            <p className="muted" data-testid="mfa-sandbox-code">
              Sandbox code: {challengeState.sandbox_code}
            </p>
          ) : null}
        </div>
      ) : null}

      <form action={challengeAction} className="stack">
        {challengeSoftError ? (
          <div className="state-banner" data-tone="error" data-testid="mfa-error" role="alert">
            <p>{challengeSoftError}</p>
          </div>
        ) : null}
        <button type="submit" disabled={challengePending} data-testid="mfa-challenge">
          {challengePending ? "Issuing…" : "Send MFA challenge"}
        </button>
      </form>

      <form action={verifyAction} className="stack">
        <label>
          MFA code
          <input
            name="code"
            type="text"
            required
            autoComplete="one-time-code"
            data-testid="mfa-code"
          />
        </label>
        {verifySoftError ? (
          <div className="state-banner" data-tone="error" data-testid="mfa-error" role="alert">
            <p>{verifySoftError}</p>
          </div>
        ) : null}
        <button type="submit" disabled={verifyPending} data-testid="mfa-verify">
          {verifyPending ? "Verifying…" : "Verify"}
        </button>
      </form>
    </div>
  );
}
