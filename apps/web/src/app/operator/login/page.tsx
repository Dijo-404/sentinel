import { RoleLogin } from "@/components/auth/role-login";

export default function OperatorLoginPage() {
  return (
    <div className="auth-page">
      <RoleLogin role="operator" />
    </div>
  );
}
