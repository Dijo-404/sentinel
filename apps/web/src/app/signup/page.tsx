import { CustomerRegisterForm } from "@/components/auth/customer-register";

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ type?: string; email?: string }>;
}) {
  const params = await searchParams;
  return (
    <div className="auth-page auth-page--night">
      <CustomerRegisterForm
        accountType={params.type === "merchant" ? "merchant" : "customer"}
        email={params.email}
      />
    </div>
  );
}
