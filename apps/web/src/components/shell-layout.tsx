import Link from "next/link";
import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  current?: "intake" | "ops" | "home";
  mode?: string;
  voiceEnabled?: boolean;
};

export function ShellLayout({
  children,
  current = "home",
  mode = "fixture",
  voiceEnabled = false,
}: Props) {
  return (
    <div className="shell">
      <header className="shell-header">
        <div className="brand">Sentinel</div>
        <nav className="nav" aria-label="Primary">
          <Link href="/intake" aria-current={current === "intake" ? "page" : undefined}>
            Text intake
          </Link>
          <Link href="/ops" aria-current={current === "ops" ? "page" : undefined}>
            Operator queue
          </Link>
        </nav>
        <div className="muted" style={{ fontSize: "0.85rem" }}>
          mode={mode} · voice={voiceEnabled ? "on" : "off"}
        </div>
      </header>
      <main className="main">{children}</main>
    </div>
  );
}
