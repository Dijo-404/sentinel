"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { motion } from "framer-motion";
import { LogoMark } from "@/components/brand/logo-mark";
import { NavIcon } from "./nav-icon";
import { WorkspaceSwitcher } from "@/components/identity/workspace-switcher";
import type { PortalRole } from "../../../tests/stubs/identity";
import type { AuthSession } from "@/lib/server/auth";
import { logoutAction } from "@/lib/server/auth-actions";
import type { NavItem } from "@/components/layout/protected-shell";

type Props = {
  role: PortalRole;
  session: AuthSession;
  nav: NavItem[];
};

function longestMatchingHref(pathname: string, nav: NavItem[]): string | null {
  let best: string | null = null;
  for (const item of nav) {
    const matches =
      pathname === item.href || pathname.startsWith(`${item.href}/`);
    if (matches && (best === null || item.href.length > best.length)) {
      best = item.href;
    }
  }
  return best;
}

export function AppSidebar({ role, session, nav }: Props) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const activeHref = longestMatchingHref(pathname, nav);

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
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              d="M4 7h16M4 12h16M4 17h16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>
          Menu
        </button>
        <span className="app-sidebar__mobile-brand">
          <LogoMark inverse size={22} />
          Sentinel
        </span>
      </div>
      {open ? (
        <button
          type="button"
          className="app-sidebar__backdrop"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      ) : null}
      <aside
        id="app-sidebar-nav"
        className={`app-sidebar${open ? " is-open" : ""}`}
      >
        <div className="app-sidebar__brand">
          <Link href="/" className="landing-wordmark">
            <LogoMark inverse size={28} />
            Sentinel
          </Link>
        </div>
        <nav className="app-sidebar__nav" aria-label={`${role} navigation`}>
          {nav.map((item) => {
            const active = item.href === activeHref;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={active ? "is-active" : undefined}
                onClick={() => setOpen(false)}
              >
                {active ? (
                  <motion.span
                    layoutId="sidebar-active"
                    className="app-sidebar__active"
                    transition={{ type: "spring", stiffness: 420, damping: 36 }}
                  />
                ) : null}
                <NavIcon label={item.label} />
                <span className="app-sidebar__label">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="app-sidebar__account">
          <div className="app-sidebar__identity">
            <span className="app-sidebar__avatar" aria-hidden="true">
              {session.user.email.slice(0, 1).toUpperCase()}
            </span>
            <span className="app-sidebar__email" title={session.user.email}>
              {session.user.email}
            </span>
          </div>
          {session.workspaces.length > 1 ? (
            <WorkspaceSwitcher
              compact
              activeAssignmentId={session.assignment.assignment_id}
              workspaces={session.workspaces.map((w) => ({
                assignment_id: w.assignment_id,
                role: w.role,
                label: w.label,
              }))}
            />
          ) : null}
          <form action={logoutAction} className="app-sidebar__logout">
            <button
              type="submit"
              className="btn btn-glass"
              data-testid="logout"
            >
              Sign out
            </button>
          </form>
        </div>
      </aside>
    </>
  );
}
