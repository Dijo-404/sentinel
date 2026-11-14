import { RoleLogin } from "@/components/auth/role-login";
import type { PortalRole } from "../../../tests/stubs/identity";

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

  return (
    <div className="auth-page auth-page--night">
      <RoleLogin role={role} next={params.next} />
    </div>
  );
}
