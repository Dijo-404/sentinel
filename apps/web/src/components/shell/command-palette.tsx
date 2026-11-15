"use client";

import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { NavItem } from "@/components/layout/protected-shell";

export type PaletteAction = { id: string; label: string; href: string; hint?: string; group: string };

/** Single-letter "G then X" shortcut per nav item; first unused letter of the label. */
export function navShortcuts(nav: NavItem[]): Map<string, NavItem> {
  const map = new Map<string, NavItem>();
  for (const item of nav) {
    const key = [...item.label.toLowerCase()].find((c) => /[a-z]/.test(c) && !map.has(c));
    if (key) map.set(key, item);
  }
  return map;
}

/** Where a typed case reference should open for this portal. */
export function caseHref(portal: string, ref: string): string {
  const id = encodeURIComponent(ref.trim());
  return portal === "operator" || portal === "supervisor" ? `/operator/cases/${id}` : `/cases/${id}`;
}

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  portal: string;
  nav: NavItem[];
  actions?: PaletteAction[];
};

/** ⌘K palette: navigate, run portal actions, or jump straight to a case reference. */
export function CommandPalette({ open, onOpenChange, portal, nav, actions = [] }: Props) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const shortcuts = navShortcuts(nav);
  const keyFor = new Map([...shortcuts].map(([k, v]) => [v.href, k]));

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  function go(href: string) {
    onOpenChange(false);
    router.push(href);
  }

  const groups = actions.reduce<Record<string, PaletteAction[]>>((acc, a) => {
    (acc[a.group] ??= []).push(a);
    return acc;
  }, {});
  const looksLikeRef = /^[a-z]{2,6}_[\w•-]{2,}$/i.test(query.trim()) || /^\d{3,}$/.test(query.trim());

  return (
    <Command.Dialog open={open} onOpenChange={onOpenChange} label="Command palette" className="cmdk" overlayClassName="cmdk-overlay" contentClassName="cmdk-content">
      <div className="cmdk__input">
        <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
          <circle cx="7" cy="7" r="5" />
          <path d="M11 11l3 3" />
        </svg>
        <Command.Input value={query} onValueChange={setQuery} placeholder="Type a page, action or case reference…" />
        <kbd className="kbd">esc</kbd>
      </div>
      <Command.List className="cmdk__list">
        <Command.Empty className="cmdk__empty">No matches. Try a case reference like case_91A.</Command.Empty>
        {looksLikeRef && (
          <Command.Group heading="Case">
            <Command.Item value={`open case ${query}`} onSelect={() => go(caseHref(portal, query))}>
              <span className="cmdk__glyph" data-tone="signal">#</span>
              Open case <code>{query.trim()}</code>
              <span className="cmdk__hint">↵</span>
            </Command.Item>
          </Command.Group>
        )}
        <Command.Group heading="Go to">
          {nav.map((item) => (
            <Command.Item key={item.href} value={`go ${item.label}`} onSelect={() => go(item.href)}>
              <span className="cmdk__glyph">→</span>
              {item.label}
              {keyFor.get(item.href) && <span className="cmdk__hint">G {keyFor.get(item.href)!.toUpperCase()}</span>}
            </Command.Item>
          ))}
        </Command.Group>
        {Object.entries(groups).map(([group, items]) => (
          <Command.Group key={group} heading={group}>
            {items.map((a) => (
              <Command.Item key={a.id} value={`${group} ${a.label}`} onSelect={() => go(a.href)}>
                <span className="cmdk__glyph" data-tone="verified">✦</span>
                {a.label}
                {a.hint && <span className="cmdk__hint">{a.hint}</span>}
              </Command.Item>
            ))}
          </Command.Group>
        ))}
      </Command.List>
    </Command.Dialog>
  );
}
