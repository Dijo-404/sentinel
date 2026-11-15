"use client";

import { useEffect, useState } from "react";

type Theme = "dark" | "light";

/** Night Ledger (dark) ↔ Paper (light). Persists per browser; boot script in layout applies it pre-paint. */
export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => {
    setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark");
  }, []);

  function flip() {
    const next: Theme = theme === "light" ? "dark" : "light";
    setTheme(next);
    if (next === "light") document.documentElement.dataset.theme = "light";
    else delete document.documentElement.dataset.theme;
    try {
      localStorage.setItem("sentinel-theme", next);
    } catch {
      // storage blocked: theme still applies for this page view
    }
  }

  return (
    <button
      type="button"
      role="switch"
      aria-checked={theme === "light"}
      aria-label="Paper (light) theme"
      className={`theme-toggle ${className ?? ""}`}
      onClick={flip}
    >
      <span className="theme-toggle__knob" aria-hidden="true">
        {theme === "light" ? "☀" : "☾"}
      </span>
    </button>
  );
}
