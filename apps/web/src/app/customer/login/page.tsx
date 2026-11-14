import { RoleLogin } from "@/components/auth/role-login";

export default function CustomerLoginPage() {
  return (
    <div className="auth-page">
      <RoleLogin role="customer" />
    </div>
  );
}
