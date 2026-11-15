import { AuthShell } from "@/components/auth/auth-shell";
import { CustomerRegisterForm } from "@/components/auth/customer-register";

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ type?: string; email?: string }>;
}) {
  const params = await searchParams;
  return (
    <AuthShell>
      <CustomerRegisterForm
        accountType={params.type === "merchant" ? "merchant" : "customer"}
        email={params.email}
      />
    </AuthShell>
  );
}
