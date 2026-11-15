"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { PORTAL_META } from "@/lib/permissions";
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
    const matches = pathname === item.href || pathname.startsWith(`${item.href}/`);
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
  const sidebar = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    sidebar.current?.focus();
    function closeOnDesktop() {
      if (window.innerWidth >= 900) setOpen(false);
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const controls = sidebar.current?.querySelectorAll<HTMLElement>(
        "a[href], button:not(:disabled), select:not(:disabled)",
      );
      const first = controls?.[0];
      const last = controls?.[controls.length - 1];
      if (
        event.shiftKey &&
        (document.activeElement === first || document.activeElement === sidebar.current)
      ) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", closeOnDesktop);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", closeOnDesktop);
      menuButton.current?.focus();
    };
  }, [open]);

  return (
    <>
      <div className="app-sidebar__mobile-bar">
        <button
          type="button"
          className="btn btn-glass app-sidebar__menu-btn"
          ref={menuButton}
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
          <LogoMark size={22} />
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
        ref={sidebar}
        id="app-sidebar-nav"
        className={`app-sidebar${open ? " is-open" : ""}`}
        tabIndex={-1}
        role={open ? "dialog" : undefined}
        aria-modal={open ? true : undefined}
        aria-label={open ? "Workspace navigation" : undefined}
      >
        <div className="app-sidebar__brand">
          <Link href="/" className="landing-wordmark">
            <LogoMark size={28} />
            Sentinel
          </Link>
        </div>
        <div className="app-sidebar__workspace">
          <span className="app-sidebar__workspace-icon" aria-hidden="true">
            <NavIcon label="Dashboard" />
          </span>
          <div>
            <strong>{PORTAL_META[role].title}</strong>
            <span>{session.assignment.label}</span>
          </div>
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
            <button type="submit" className="btn btn-glass" data-testid="logout">
              Sign out
            </button>
          </form>
        </div>
      </aside>
    </>
  );
}
