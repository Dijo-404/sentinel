"use client";

import Link from "next/link";
import { useActionState } from "react";
import type { PortalRole } from "../../../tests/stubs/identity";
import { PORTAL_META } from "@/lib/permissions";
import { loginAction, type ActionResult } from "@/lib/server/auth-actions";

type Props = {
  role: PortalRole;
  next?: string;
};

const initial: ActionResult | null = null;

export function RoleLogin({ role, next }: Props) {
  const meta = PORTAL_META[role];
  const [state, formAction, pending] = useActionState(loginAction, initial);
  const showRegister = role === "customer";

  return (
    <div className="auth-card panel stack" data-testid="role-login" data-role={role}>
      <div>
        <p className="brand auth-brand">Sentinel</p>
        <h1>{meta.title}</h1>
        <p className="muted">{meta.description}</p>
        <p className="fixture-banner" role="status">
          Demo authentication — fixture identity stub
        </p>
      </div>

      <form action={formAction} className="stack" noValidate>
        <input type="hidden" name="role" value={role} />
        {next ? <input type="hidden" name="next" value={next} /> : null}

        <label>
          {role === "customer" ? "Email or mobile" : "Work email"}
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

        {showRegister ? (
          <label>
            Preferred language
            <select name="language" defaultValue="en" aria-label="Preferred language">
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="ta">Tamil</option>
            </select>
          </label>
        ) : null}

        {state && !state.ok ? (
          <div
            className="state-banner"
            data-tone="error"
            data-testid="login-error"
            role="alert"
          >
            <p>{state.message}</p>
            {state.workspaces && state.workspaces.length > 0 ? (
              <ul data-testid="authorized-workspaces">
                {state.workspaces.map((w) => (
                  <li key={w.href}>
                    <Link href={w.href}>{w.label}</Link>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}

        <div className="row">
          <button type="submit" disabled={pending} data-testid="login-submit">
            {pending ? "Signing in…" : "Sign in"}
          </button>
        </div>
      </form>

      {showRegister ? (
        <p className="muted">
          New here?{" "}
          <Link href="/customer/register" data-testid="register-link">
            Create a customer account
          </Link>
        </p>
      ) : (
        <p className="muted" data-testid="no-signup">
          Staff accounts are invitation-only. There is no public sign-up for this
          portal.
        </p>
      )}
    </div>
  );
}
