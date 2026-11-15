"use client";

import Link from "next/link";
import { useActionState } from "react";
import { useSearchParams } from "next/navigation";
import { resetPasswordAction, type ChallengeActionResult } from "@/lib/server/auth-actions";

const initial: ChallengeActionResult | null = null;

export function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const emailFromQuery = searchParams.get("email") ?? "";
  const [state, formAction, pending] = useActionState(resetPasswordAction, initial);

  return (
    <div className="auth-card panel stack" data-testid="auth-reset">
      <div>
        <p className="brand auth-brand">Sentinel</p>
        <h1>Reset password</h1>
        <p className="muted">
          Enter the sandbox reset code from identity and choose a new password.
        </p>
      </div>

      {state && state.ok ? (
        <div className="state-banner" data-tone="empty" data-testid="reset-success" role="status">
          <p>{state.message}</p>
          <p>
            <Link href="/login">Sign in</Link>
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
              defaultValue={emailFromQuery}
              autoComplete="email"
              data-testid="reset-email"
            />
          </label>
          <label>
            Reset code
            <input
              name="code"
              type="text"
              required
              autoComplete="one-time-code"
              data-testid="reset-code"
            />
          </label>
          <label>
            New password (min 8 characters)
            <input
              name="new_password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              data-testid="reset-password"
            />
          </label>

          {state && !state.ok ? (
            state.peerError ? (
              <div className="state-banner" data-tone="error" data-testid="peer-error" role="alert">
                <strong>Identity unavailable</strong>
                <p className="muted" style={{ margin: "0.35rem 0 0" }}>
                  {state.message}
                </p>
              </div>
            ) : (
              <div
                className="state-banner"
                data-tone="error"
                data-testid="reset-error"
                role="alert"
              >
                <p>{state.message}</p>
              </div>
            )
          ) : null}

          <button type="submit" disabled={pending} data-testid="reset-submit">
            {pending ? "Updating…" : "Update password"}
          </button>
        </form>
      )}

      <p className="muted">
        <Link href="/auth/forgot-password">Request a new code</Link>
      </p>
    </div>
  );
}
