"use client";

import Link from "next/link";
import { useActionState } from "react";
import {
  registerCustomerAction,
  type ActionResult,
} from "@/lib/server/auth-actions";

const initial: ActionResult | null = null;

export function CustomerRegisterForm() {
  const [state, formAction, pending] = useActionState(
    registerCustomerAction,
    initial,
  );

  return (
    <div className="auth-card panel stack" data-testid="customer-register">
      <div>
        <p className="brand auth-brand">Sentinel</p>
        <h1>Create customer account</h1>
        <p className="muted">
          Server assigns the customer role. Privileged fields are rejected.
        </p>
      </div>

      <form action={formAction} className="stack" noValidate>
        <label>
          Full name
          <input name="display_name" required data-testid="register-name" />
        </label>
        <label>
          Email
          <input
            name="email"
            type="email"
            required
            autoComplete="email"
            data-testid="register-email"
          />
        </label>
        <label>
          Password (min 8 characters)
          <input
            name="password"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            data-testid="register-password"
          />
        </label>
        <label>
          Preferred language
          <select name="language" defaultValue="en">
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="ta">Tamil</option>
          </select>
        </label>
        <label className="row" style={{ alignItems: "flex-start" }}>
          <input type="checkbox" name="terms" required value="accepted" />
          <span>I accept the terms of use</span>
        </label>

        {state && !state.ok ? (
          <div className="state-banner" data-tone="error" role="alert">
            {state.message}
          </div>
        ) : null}

        <button type="submit" disabled={pending} data-testid="register-submit">
          {pending ? "Creating…" : "Create account"}
        </button>
      </form>

      <p className="muted">
        Already registered? <Link href="/customer/login">Sign in</Link>
      </p>
    </div>
  );
}
