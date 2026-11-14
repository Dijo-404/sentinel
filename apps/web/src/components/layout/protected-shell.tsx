import type { ReactNode } from "react";
import type { PortalRole } from "../../../tests/stubs/identity";
import type { AuthSession } from "@/lib/server/auth";
import { AppSidebar } from "@/components/shell/app-sidebar";

export type NavItem = { href: string; label: string };

type Props = {
  role: PortalRole;
  session: AuthSession;
  nav: NavItem[];
  children: ReactNode;
};

export function ProtectedShell({ role, session, nav, children }: Props) {
  return (
    <div className="portal-shell" data-portal={role}>
      <AppSidebar role={role} session={session} nav={nav} />
      <main className="portal-main stack">{children}</main>
    </div>
  );
}
