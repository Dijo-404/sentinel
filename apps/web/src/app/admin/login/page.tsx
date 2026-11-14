import { RoleLogin } from "@/components/auth/role-login";

export default function AdminLoginPage() {
  return (
    <div className="auth-page">
      <RoleLogin role="admin" />
    </div>
  );
}
