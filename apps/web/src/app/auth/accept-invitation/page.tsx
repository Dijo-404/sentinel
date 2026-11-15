import { AuthShell } from "@/components/auth/auth-shell";
import { Suspense } from "react";
import { AcceptInvitationForm } from "@/components/auth/accept-invitation-form";

export default function AuthAcceptInvitationPage() {
  return (
    <AuthShell>
      <Suspense
        fallback={
          <div className="auth-card panel stack">
            <p className="brand auth-brand">Sentinel</p>
            <h1>Accept invitation</h1>
            <p className="muted">Loading…</p>
          </div>
        }
      >
        <AcceptInvitationForm />
      </Suspense>
    </AuthShell>
  );
}
