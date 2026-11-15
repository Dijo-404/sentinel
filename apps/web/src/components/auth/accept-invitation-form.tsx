"use client";

import { useActionState } from "react";
import { useSearchParams } from "next/navigation";
import { acceptInvitationAction, type ActionResult } from "@/lib/server/auth-actions";

const initial: ActionResult | null = null;

export function AcceptInvitationForm() {
  const searchParams = useSearchParams();
  const tokenFromQuery = searchParams.get("token") ?? "";
  const [state, formAction, pending] = useActionState(acceptInvitationAction, initial);

  return (
    <div className="auth-card panel stack" data-testid="accept-invitation">
      <p className="brand auth-brand">Sentinel</p>
      <h1>Accept invitation</h1>
      <p className="muted">Create your staff password with the invite token from your email.</p>

      <form action={formAction} className="stack" noValidate>
        <label>
          Invitation token
          <input
            name="token"
            type="text"
            required
            defaultValue={tokenFromQuery}
            autoComplete="off"
            data-testid="invite-token"
          />
        </label>
        <label>
          Work email
          <input
            name="email"
            type="email"
            required
            autoComplete="username"
            data-testid="invite-email"
          />
        </label>
        <label>
          Display name
          <input
            name="display_name"
            type="text"
            autoComplete="name"
            data-testid="invite-display-name"
          />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            data-testid="invite-password"
          />
        </label>

        {state && !state.ok ? (
          <div className="state-banner" data-tone="error" data-testid="invite-error" role="alert">
            <p>{state.message}</p>
          </div>
        ) : null}

        <button type="submit" disabled={pending} data-testid="invite-submit">
          {pending ? "Accepting…" : "Accept invitation"}
        </button>
      </form>
    </div>
  );
}
