import { RoleLogin } from "@/components/auth/role-login";

export default function MerchantLoginPage() {
  return (
    <div className="auth-page">
      <RoleLogin role="merchant" />
    </div>
  );
}
