"use client";

import Link from "next/link";
import { useActionState, useId, useRef, useState } from "react";
import {
  registerCustomerAction,
  registerMerchantAction,
  type ActionResult,
} from "@/lib/server/auth-actions";

const initial: ActionResult | null = null;

export function CustomerRegisterForm({
  email = "",
  accountType = "customer",
}: {
  email?: string;
  accountType?: "customer" | "merchant";
}) {
  const [type, setType] = useState(accountType);
  const [customerState, customerAction, customerPending] = useActionState(
    registerCustomerAction,
    initial,
  );
  const [merchantState, merchantAction, merchantPending] = useActionState(
    registerMerchantAction,
    initial,
  );
  const [state, formAction, pending] =
    type === "merchant"
      ? [merchantState, merchantAction, merchantPending]
      : [customerState, customerAction, customerPending];
  const id = useId();
  const tabs = useRef<Array<HTMLButtonElement | null>>([]);

  return (
    <div className="auth-card panel stack" data-testid="customer-register">
      <div>
        <p className="brand auth-brand">Sentinel</p>
        <h1>Create an account</h1>
        <p className="muted">Choose how you’ll use Sentinel. Staff access is by invitation.</p>
      </div>

      <div role="tablist" aria-label="Account type" className="row">
        {(["customer", "merchant"] as const).map((value, index) => (
          <button
            key={value}
            type="button"
            role="tab"
            id={`${id}-${value}`}
            className={type === value ? undefined : "secondary"}
            aria-controls={`${id}-panel`}
            aria-selected={type === value}
            tabIndex={type === value ? 0 : -1}
            ref={(element) => {
              tabs.current[index] = element;
            }}
            onClick={() => setType(value)}
            onKeyDown={(event) => {
              if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
              event.preventDefault();
              const target = event.key === "Home" ? 0 : event.key === "End" ? 1 : 1 - index;
              setType(target === 0 ? "customer" : "merchant");
              tabs.current[target]?.focus();
            }}
          >
            {value === "customer" ? "Customer" : "Merchant"}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-${type}`}>
        <form action={formAction} className="stack">
          <label>
            Full name
            <input name="display_name" required autoComplete="name" data-testid="register-name" />
          </label>
          <label>
            Email
            <input
              name="email"
              defaultValue={email}
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
          {type === "merchant" ? (
            <label>
              Business name
              <input name="business_name" required autoComplete="organization" />
            </label>
          ) : null}
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
      </div>

      <p className="muted">
        Already registered? <Link href="/login">Sign in</Link>
      </p>
    </div>
  );
}
