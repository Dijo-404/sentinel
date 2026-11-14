import { ProtectedShell } from "@/components/layout/protected-shell";
import { requireRole } from "@/lib/server/authorization";
import { PORTAL_NAV } from "@/lib/portal-nav";

export default async function SupervisorProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireRole("supervisor");
  return (
    <ProtectedShell
      role="supervisor"
      session={session}
      nav={PORTAL_NAV.supervisor}
    >
      {children}
    </ProtectedShell>
  );
}
