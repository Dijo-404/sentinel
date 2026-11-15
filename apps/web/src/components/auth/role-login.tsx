"use client";

import Link from "next/link";
import { useActionState } from "react";
import { loginAction, type ActionResult } from "@/lib/server/auth-actions";

export function RoleLogin({ next }: { next?: string }) {
  const [state, formAction, pending] = useActionState(loginAction, null as ActionResult | null);
  return (
    <div className="auth-card panel stack" data-testid="role-login">
      <div>
        <p className="brand auth-brand">Sentinel</p>
        <h1>Sign in</h1>
        <p className="muted">Continue to your workspace.</p>
      </div>
      <form action={formAction} className="stack">
        {next ? <input type="hidden" name="next" value={next} /> : null}
        <label>
          Email
          <input
            name="email"
            type="email"
            autoComplete="username"
            required
            data-testid="login-email"
          />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            data-testid="login-password"
          />
        </label>
        {state && !state.ok ? (
          <div className="state-banner" data-tone="error" data-testid="login-error" role="alert">
            {state.message}
          </div>
        ) : null}
        <button type="submit" disabled={pending} data-testid="login-submit">
          {pending ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="muted">
        New here?{" "}
        <Link href="/signup" data-testid="register-link">
          Create an account
        </Link>
      </p>
      <p className="muted">Staff accounts are invitation-only.</p>
      <details className="demo-users" data-testid="demo-users">
        <summary>Sandbox seed accounts</summary>
        <p className="muted">
          Local sandbox accounts use the configured identity demo password. See the sandbox
          credentials guide.
        </p>
      </details>
    </div>
  );
}
