"use client";

import Link from "next/link";
import { useActionState } from "react";
import {
  forgotPasswordAction,
  type ChallengeActionResult,
} from "@/lib/server/auth-actions";

const initial: ChallengeActionResult | null = null;

export function ForgotPasswordForm() {
  const [state, formAction, pending] = useActionState(
    forgotPasswordAction,
    initial,
  );

  return (
    <div className="auth-card panel stack" data-testid="auth-forgot">
      <div>
        <p className="brand auth-brand">Sentinel</p>
        <h1>Forgot password</h1>
        <p className="muted">
          Enter your email. If an account exists, reset instructions are issued
          through identity (sandbox delivery log — no invented email body here).
        </p>
      </div>

      {state && state.ok ? (
        <div
          className="state-banner"
          data-tone="empty"
          data-testid="forgot-success"
          role="status"
        >
          <p>{state.message}</p>
          <p className="muted">
            Have a code?{" "}
            <Link href="/auth/reset-password">Reset password</Link>
          </p>
        </div>
      ) : (
        <form action={formAction} className="stack" noValidate>
          <label>
            Email
            <input
              name="email"
              type="email"
              required
              autoComplete="email"
              data-testid="forgot-email"
            />
          </label>

          {state && !state.ok ? (
            state.peerError ? (
              <div
                className="state-banner"
                data-tone="error"
                data-testid="peer-error"
                role="alert"
              >
                <strong>Identity unavailable</strong>
                <p className="muted" style={{ margin: "0.35rem 0 0" }}>
                  {state.message}
                </p>
              </div>
            ) : (
              <div
                className="state-banner"
                data-tone="error"
                data-testid="forgot-error"
                role="alert"
              >
                <p>{state.message}</p>
              </div>
            )
          ) : null}

          <button type="submit" disabled={pending} data-testid="forgot-submit">
            {pending ? "Sending…" : "Send reset instructions"}
          </button>
        </form>
      )}

      <p className="muted">
        <Link href="/login">Back to sign in</Link>
      </p>
    </div>
  );
}
