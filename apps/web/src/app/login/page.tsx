import { redirect } from "next/navigation";
import { RoleLogin } from "@/components/auth/role-login";
import type { PortalRole } from "../../../tests/stubs/identity";
import { getAuthSession, portalPath } from "@/lib/server/auth";

const PORTALS: PortalRole[] = [
  "customer",
  "merchant",
  "operator",
  "supervisor",
  "risk",
  "admin",
];

function parsePortal(value: string | undefined): PortalRole | undefined {
  if (!value) return undefined;
  return PORTALS.includes(value as PortalRole)
    ? (value as PortalRole)
    : undefined;
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ portal?: string; next?: string }>;
}) {
  const params = await searchParams;
  const role = parsePortal(params.portal);
  const session = await getAuthSession();
  if (session) {
    redirect(portalPath(session.assignment.role));
  }

  return (
    <div className="auth-page auth-page--night">
      <RoleLogin role={role} next={params.next} />
    </div>
  );
}
