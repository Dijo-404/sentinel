import { ProtectedShell } from "@/components/layout/protected-shell";
import { requireRole } from "@/lib/server/authorization";
import { PORTAL_NAV } from "@/lib/portal-nav";

export default async function AdminProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireRole("admin");
  return (
    <ProtectedShell role="admin" session={session} nav={PORTAL_NAV.admin}>
      {children}
    </ProtectedShell>
  );
}
