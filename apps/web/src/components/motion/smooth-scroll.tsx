"use client";

import Lenis from "lenis";
import { frame, cancelFrame } from "framer-motion";
import { useEffect } from "react";

/** Lenis smooth scroll for marketing pages only; portals keep native scroll. */
export function SmoothScroll() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const lenis = new Lenis({ lerp: 0.1, anchors: true });
    // Drive Lenis from framer-motion's loop so scroll-linked values stay in sync.
    const tick = ({ timestamp }: { timestamp: number }) => lenis.raf(timestamp);
    frame.update(tick, true);
    return () => {
      cancelFrame(tick);
      lenis.destroy();
    };
  }, []);
  return null;
}
