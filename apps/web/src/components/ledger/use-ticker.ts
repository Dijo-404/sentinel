"use client";

import { useEffect, useState } from "react";

/**
 * Monotonic tick for live surfaces. Pauses while the tab is hidden or `paused` is set.
 * Data keeps updating under reduced motion; only animations are suppressed (by CSS).
 */
export function useTicker(intervalMs: number, paused = false): number {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (paused) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") setTick((t) => t + 1);
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs, paused]);
  return tick;
}
