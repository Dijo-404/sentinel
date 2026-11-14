import { ProtectedShell } from "@/components/layout/protected-shell";
import { requireAnyRole } from "@/lib/server/authorization";
import { opsPortalNav } from "@/lib/portal-nav";

export default async function OperatorProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await requireAnyRole(["operator", "supervisor"], "operator");
  return (
    <ProtectedShell
      role="operator"
      session={session}
      nav={opsPortalNav("operator")}
    >
      {children}
    </ProtectedShell>
  );
}
