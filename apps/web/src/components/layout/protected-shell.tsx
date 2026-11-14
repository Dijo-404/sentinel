import Link from "next/link";
import type { ReactNode } from "react";
import type { PortalRole } from "../../../tests/stubs/identity";
import type { AuthSession } from "@/lib/server/auth";
import { logoutAction } from "@/lib/server/auth-actions";
import { PORTAL_META } from "@/lib/permissions";

export type NavItem = { href: string; label: string };

type Props = {
  role: PortalRole;
  session: AuthSession;
  nav: NavItem[];
  children: ReactNode;
};

export function ProtectedShell({ role, session, nav, children }: Props) {
  const meta = PORTAL_META[role];
  return (
    <div className="shell portal-shell" data-portal={role}>
      <header className="shell-header">
        <div>
          <div className="brand">Sentinel</div>
          <div className="muted" style={{ fontSize: "0.85rem" }}>
            {meta.title} · {session.user.display_name}
          </div>
        </div>
        <nav className="nav" aria-label={`${role} navigation`}>
          {nav.map((item) => (
            <Link key={item.href} href={item.href}>
              {item.label}
            </Link>
          ))}
        </nav>
        <form action={logoutAction}>
          <button type="submit" className="secondary" data-testid="logout">
            Sign out
          </button>
        </form>
      </header>
      <main className="main stack">{children}</main>
    </div>
  );
}
