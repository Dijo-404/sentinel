import { redirect } from "next/navigation";
import { RoleLogin } from "@/components/auth/role-login";
import { getAuthSession, portalPath } from "@/lib/server/auth";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ portal?: string; next?: string }>;
}) {
  const params = await searchParams;
  const session = await getAuthSession();
  if (session) {
    redirect(portalPath(session.assignment.role));
  }

  return (
    <div className="auth-page auth-page--night">
      <RoleLogin next={params.next} />
    </div>
  );
}
