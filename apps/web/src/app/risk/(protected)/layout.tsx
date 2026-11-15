import { ProtectedShell } from "@/components/layout/protected-shell";
import { requireRole } from "@/lib/server/authorization";
import { PORTAL_NAV } from "@/lib/portal-nav";

export default async function RiskProtectedLayout({ children }: { children: React.ReactNode }) {
  const session = await requireRole("risk");
  return (
    <ProtectedShell role="risk" session={session} nav={PORTAL_NAV.risk}>
      {children}
    </ProtectedShell>
  );
}
