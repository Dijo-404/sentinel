import { Suspense } from "react";
import { AcceptInvitationForm } from "@/components/auth/accept-invitation-form";

export default function AuthAcceptInvitationPage() {
  return (
    <div className="auth-page">
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
    </div>
  );
}
