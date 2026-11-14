import { ProtectedShell } from "@/components/layout/protected-shell";
import { requireRole } from "@/lib/server/authorization";
import { PORTAL_NAV } from "@/lib/portal-nav";

export default async function MerchantProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireRole("merchant");
  return (
    <ProtectedShell role="merchant" session={session} nav={PORTAL_NAV.merchant}>
      {children}
    </ProtectedShell>
  );
}
