"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import type { PortalRole } from "../../../tests/stubs/identity";
import type { AuthSession } from "@/lib/server/auth";
import { logoutAction } from "@/lib/server/auth-actions";
import { PORTAL_META } from "@/lib/permissions";
import type { NavItem } from "@/components/layout/protected-shell";

type Props = {
  role: PortalRole;
  session: AuthSession;
  nav: NavItem[];
};

export function AppSidebar({ role, session, nav }: Props) {
  const pathname = usePathname();
  const meta = PORTAL_META[role];
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="app-sidebar__mobile-bar">
        <button
          type="button"
          className="btn btn-glass app-sidebar__menu-btn"
          aria-expanded={open}
          aria-controls="app-sidebar-nav"
          onClick={() => setOpen((v) => !v)}
        >
          Menu
        </button>
        <span className="app-sidebar__mobile-brand">Sentinel</span>
      </div>
      <aside
        id="app-sidebar-nav"
        className={`app-sidebar${open ? " is-open" : ""}`}
      >
        <div className="app-sidebar__brand">
          <Link href="/" className="landing-wordmark">
            Sentinel
          </Link>
          <p className="app-sidebar__role">
            {meta.title}
            <span className="app-sidebar__user">{session.user.display_name}</span>
          </p>
        </div>
        <nav className="app-sidebar__nav" aria-label={`${role} navigation`}>
          {nav.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={active ? "is-active" : undefined}
                onClick={() => setOpen(false)}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <form action={logoutAction} className="app-sidebar__logout">
          <button type="submit" className="btn btn-glass" data-testid="logout">
            Sign out
          </button>
        </form>
      </aside>
    </>
  );
}
