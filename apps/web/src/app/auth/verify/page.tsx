import { AuthShell } from "@/components/auth/auth-shell";
import { VerifyContactForm } from "@/components/auth/verify-contact-form";

export default function AuthVerifyPage() {
  return (
    <AuthShell>
      <VerifyContactForm />
    </AuthShell>
  );
}
