import { ProtectedShell } from "@/components/layout/protected-shell";
import { requireRole } from "@/lib/server/authorization";
import { PORTAL_NAV } from "@/lib/portal-nav";

export default async function CustomerProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireRole("customer");
  return (
    <ProtectedShell role="customer" session={session} nav={PORTAL_NAV.customer}>
      {children}
    </ProtectedShell>
  );
}
