"use client";

import Link from "next/link";
import { useActionState, useState } from "react";
import type { PortalRole } from "../../../tests/stubs/identity";
import { ROLE_LABELS } from "../../../tests/stubs/identity";
import { PORTAL_META } from "@/lib/permissions";
import { loginAction, type ActionResult } from "@/lib/server/auth-actions";

const PORTALS: PortalRole[] = [
  "customer",
  "merchant",
  "operator",
  "supervisor",
  "risk",
  "admin",
];

type Props = {
  /** Preselected workspace (e.g. from `?portal=`). */
  role?: PortalRole;
  next?: string;
};

const initial: ActionResult | null = null;

export function RoleLogin({ role = "customer", next }: Props) {
  const [selectedRole, setSelectedRole] = useState<PortalRole>(role);
  const meta = PORTAL_META[selectedRole];
  const [state, formAction, pending] = useActionState(loginAction, initial);
  const showRegister = selectedRole === "customer";

  return (
    <div
      className="auth-card panel stack"
      data-testid="role-login"
      data-role={selectedRole}
    >
      <div>
        <p className="brand auth-brand">Sentinel</p>
        <h1>Sign in</h1>
        <p className="muted">{meta.description}</p>
        <p className="fixture-banner" role="status">
          Demo authentication — fixture identity stub
        </p>
      </div>

      <form action={formAction} className="stack" noValidate>
        {next ? <input type="hidden" name="next" value={next} /> : null}

        <label>
          Workspace
          <select
            name="role"
            required
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value as PortalRole)}
            data-testid="login-workspace"
            aria-label="Workspace"
          >
            {PORTALS.map((r) => (
              <option key={r} value={r}>
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
        </label>

        <label>
          {selectedRole === "customer" ? "Email or mobile" : "Work email"}
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
            <select
              name="language"
              defaultValue="en"
              aria-label="Preferred language"
            >
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
          Staff accounts are invitation-only. There is no public sign-up for
          this portal.
        </p>
      )}

      <details className="demo-users" data-testid="demo-users">
        <summary>Demo users</summary>
        <ul>
          <li>customer@example.test / demo-customer</li>
          <li>merchant@example.test / demo-merchant</li>
          <li>operator@example.test / demo-operator</li>
          <li>supervisor@example.test / demo-supervisor</li>
          <li>risk@example.test / demo-risk</li>
          <li>admin@example.test / demo-admin</li>
        </ul>
      </details>
    </div>
  );
}
