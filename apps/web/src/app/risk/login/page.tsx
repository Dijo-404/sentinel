import { RoleLogin } from "@/components/auth/role-login";

export default function RiskLoginPage() {
  return (
    <div className="auth-page">
      <RoleLogin role="risk" />
    </div>
  );
}
