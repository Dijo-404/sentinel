import type { ReactNode } from "react";
import type { PortalRole } from "../../../tests/stubs/identity";
import type { AuthSession } from "@/lib/server/auth";
import { AppSidebar } from "@/components/shell/app-sidebar";
import { PortalCaseShell } from "@/components/shell/portal-case-shell";

export type NavItem = { href: string; label: string };

type Props = {
  role: PortalRole;
  session: AuthSession;
  nav: NavItem[];
  children: ReactNode;
};

export function ProtectedShell({ role, session, nav, children }: Props) {
  return (
    <PortalCaseShell role={role}>
      <div className="portal-shell" data-portal={role}>
        <AppSidebar role={role} session={session} nav={nav} />
        <main className="portal-main stack">{children}</main>
      </div>
    </PortalCaseShell>
  );
}
