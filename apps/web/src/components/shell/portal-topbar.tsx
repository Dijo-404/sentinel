"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { NavItem } from "@/components/layout/protected-shell";
import { ThemeToggle } from "@/components/motion/theme-toggle";
import { CommandPalette, navShortcuts, type PaletteAction } from "./command-palette";

const PORTAL_ACTIONS: Record<string, PaletteAction[]> = {
  operator: [
    {
      id: "next",
      label: "Take next case in queue",
      href: "/operator/queue",
      hint: "N",
      group: "Actions",
    },
    { id: "esc", label: "Open escalations", href: "/operator/escalations", group: "Actions" },
  ],
  supervisor: [
    {
      id: "appr",
      label: "Review pending approvals",
      href: "/supervisor/approvals",
      hint: "A",
      group: "Actions",
    },
    { id: "hist", label: "Approval history", href: "/supervisor/history", group: "Actions" },
  ],
  merchant: [
    { id: "refunds", label: "Review refund requests", href: "/merchant/refunds", group: "Actions" },
  ],
  risk: [{ id: "holds", label: "Manage active holds", href: "/risk/holds", group: "Actions" }],
  admin: [{ id: "invite", label: "Invite a user", href: "/admin/users/invite", group: "Actions" }],
  customer: [
    { id: "report", label: "Report a problem", href: "/customer/report", group: "Actions" },
  ],
};

function isTyping(el: EventTarget | null) {
  const t = el as HTMLElement | null;
  return (
    !!t &&
    (t.tagName === "INPUT" ||
      t.tagName === "TEXTAREA" ||
      t.tagName === "SELECT" ||
      t.isContentEditable)
  );
}

/** Portal top bar: ⌘K, G-then-letter navigation, ? shortcut sheet, density + theme. */
export function PortalTopbar({
  portal,
  nav,
  mode,
}: {
  portal: string;
  nav: NavItem[];
  mode: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [help, setHelp] = useState(false);
  const [dense, setDense] = useState(false);
  const gPending = useRef<number | null>(null);
  const shortcuts = navShortcuts(nav);

  useEffect(() => {
    setDense(document.documentElement.dataset.density === "compact");
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
        return;
      }
      if (open || isTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "?") {
        setHelp((v) => !v);
        return;
      }
      if (e.key === "Escape") setHelp(false);
      if (gPending.current !== null) {
        const item = shortcuts.get(e.key.toLowerCase());
        window.clearTimeout(gPending.current);
        gPending.current = null;
        if (item) router.push(item.href);
        return;
      }
      if (e.key === "g") gPending.current = window.setTimeout(() => (gPending.current = null), 900);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, router, shortcuts]);

  function toggleDensity() {
    const next = !dense;
    setDense(next);
    if (next) document.documentElement.dataset.density = "compact";
    else delete document.documentElement.dataset.density;
    try {
      localStorage.setItem("sentinel-density", next ? "compact" : "comfortable");
    } catch {
      // storage blocked: density applies for this view only
    }
  }

  return (
    <div className="topbar">
      <button
        type="button"
        className="topbar__search"
        onClick={() => setOpen(true)}
        data-testid="open-palette"
      >
        <svg
          width="15"
          height="15"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          aria-hidden="true"
        >
          <circle cx="7" cy="7" r="5" />
          <path d="M11 11l3 3" />
        </svg>
        Search or jump to…
        <kbd className="kbd">⌘K</kbd>
      </button>
      <div className="topbar__right">
        <span className="topbar__mode" title="NEXT_PUBLIC_SHELL_MODE">
          <span className="live-dot" aria-hidden="true" />
          {mode}
        </span>
        <button
          type="button"
          className="topbar__icon"
          aria-pressed={dense}
          onClick={toggleDensity}
          aria-label="Compact density"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            aria-hidden="true"
          >
            <path d={dense ? "M2 4h12M2 7h12M2 10h12M2 13h12" : "M2 4h12M2 8h12M2 12h12"} />
          </svg>
        </button>
        <button
          type="button"
          className="topbar__icon"
          onClick={() => setHelp(true)}
          aria-label="Keyboard shortcuts"
        >
          ?
        </button>
        <ThemeToggle />
      </div>
      <CommandPalette
        open={open}
        onOpenChange={setOpen}
        portal={portal}
        nav={nav}
        actions={PORTAL_ACTIONS[portal]}
      />
      {help && (
        <div
          className="shortcut-sheet"
          role="dialog"
          aria-modal="true"
          aria-label="Keyboard shortcuts"
          onClick={() => setHelp(false)}
        >
          <div className="pnl shortcut-sheet__card" onClick={(e) => e.stopPropagation()}>
            <div className="shortcut-sheet__head">
              <h2>Keyboard shortcuts</h2>
              <button
                type="button"
                className="topbar__icon"
                onClick={() => setHelp(false)}
                aria-label="Close shortcuts"
              >
                ✕
              </button>
            </div>
            <dl>
              <div>
                <dt>
                  <kbd className="kbd">⌘</kbd> <kbd className="kbd">K</kbd>
                </dt>
                <dd>Command palette</dd>
              </div>
              <div>
                <dt>
                  <kbd className="kbd">?</kbd>
                </dt>
                <dd>This sheet</dd>
              </div>
              {[...shortcuts].map(([k, item]) => (
                <div key={item.href}>
                  <dt>
                    <kbd className="kbd">G</kbd> <kbd className="kbd">{k.toUpperCase()}</kbd>
                  </dt>
                  <dd>{item.label}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      )}
    </div>
  );
}
