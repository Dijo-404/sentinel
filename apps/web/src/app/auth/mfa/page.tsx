import { AuthShell } from "@/components/auth/auth-shell";
import { MfaChallengeForm } from "@/components/auth/mfa-challenge-form";

export default function AuthMfaPage() {
  return (
    <AuthShell>
      <MfaChallengeForm />
    </AuthShell>
  );
}
