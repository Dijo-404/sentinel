import type { ReactNode } from "react";
import type { PortalRole } from "../../../tests/stubs/identity";
import type { AuthSession } from "@/lib/server/auth";
import { AppSidebar } from "@/components/shell/app-sidebar";
import { PortalCaseShell } from "@/components/shell/portal-case-shell";
import { PortalTopbar } from "@/components/shell/portal-topbar";

export type NavItem = { href: string; label: string };

type Props = {
  role: PortalRole;
  session: AuthSession;
  nav: NavItem[];
  children: ReactNode;
};

/** Label exactly what is configured; never imply live or simulated when it isn't known. */
function modeLabel(): string {
  const mode = process.env.NEXT_PUBLIC_SHELL_MODE;
  if (mode === "fixture") return "fixture data";
  if (mode === "real-peers") return "real peers";
  return "mode unset";
}

export function ProtectedShell({ role, session, nav, children }: Props) {
  return (
    <PortalCaseShell role={role}>
      <div className="portal-shell" data-portal={role}>
        <AppSidebar role={role} session={session} nav={nav} />
        <main className="portal-main stack">
          <PortalTopbar portal={role} nav={nav} mode={modeLabel()} />
          {children}
        </main>
      </div>
    </PortalCaseShell>
  );
}
