import { Suspense } from "react";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export default function AuthResetPasswordPage() {
  return (
    <div className="auth-page">
      <Suspense
        fallback={
          <div className="auth-card panel stack">
            <p className="brand auth-brand">Sentinel</p>
            <h1>Reset password</h1>
            <p className="muted">Loading…</p>
          </div>
        }
      >
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
