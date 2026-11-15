import { ProtectedShell } from "@/components/layout/protected-shell";
import { requireAnyRole } from "@/lib/server/authorization";
import { opsPortalNav } from "@/lib/portal-nav";

export default async function SupervisorProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireAnyRole(["operator", "supervisor"], "supervisor");
  const portal = session.assignment.role === "supervisor" ? "supervisor" : "operator";
  return (
    <ProtectedShell role={portal} session={session} nav={opsPortalNav(portal)}>
      {children}
    </ProtectedShell>
  );
}
