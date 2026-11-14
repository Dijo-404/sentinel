import { RoleLogin } from "@/components/auth/role-login";

export default function SupervisorLoginPage() {
  return (
    <div className="auth-page">
      <RoleLogin role="supervisor" />
    </div>
  );
}
