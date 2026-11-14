import { ProtectedShell } from "@/components/layout/protected-shell";
import { requireRole } from "@/lib/server/authorization";
import { PORTAL_NAV } from "@/lib/portal-nav";

export default async function OperatorProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireRole("operator");
  return (
    <ProtectedShell role="operator" session={session} nav={PORTAL_NAV.operator}>
      {children}
    </ProtectedShell>
  );
}
