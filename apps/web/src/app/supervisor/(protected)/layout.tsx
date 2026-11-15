import { ProtectedShell } from "@/components/layout/protected-shell";
import { requireAnyRole } from "@/lib/server/authorization";
import { opsPortalNav } from "@/lib/portal-nav";

export default async function SupervisorProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireAnyRole(["operator", "supervisor"], "supervisor");
  return (
    <ProtectedShell role="supervisor" session={session} nav={opsPortalNav("supervisor")}>
      {children}
    </ProtectedShell>
  );
}
