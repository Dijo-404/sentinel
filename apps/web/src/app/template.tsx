"use client";

import { MotionConfig, motion } from "framer-motion";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const PORTALS = ["/customer", "/merchant", "/operator", "/supervisor", "/risk", "/admin"];
const ENTRY = ["/", "/login"];

/** Last path seen on this client; survives navigations because the module stays loaded. */
let previousPath: string | null = null;

/** Curtain only when crossing from the marketing/login entry into a portal. Pure. */
export function crossesIntoPortal(from: string | null, to: string): boolean {
  return !!from && ENTRY.includes(from) && PORTALS.some((p) => to === p || to.startsWith(`${p}/`));
}

/** Per-navigation page transition: calm fade-rise everywhere, a curtain wipe on portal entry. */
export default function Template({ children }: { children: ReactNode }) {
  const path = usePathname() ?? "/";
  const curtain = crossesIntoPortal(previousPath, path);
  previousPath = path;

  return (
    <MotionConfig reducedMotion="user">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      >
        {children}
      </motion.div>
      {curtain && (
        <motion.div
          className="route-curtain"
          aria-hidden="true"
          initial={{ scaleY: 1 }}
          animate={{ scaleY: 0 }}
          transition={{ duration: 0.7, ease: [0.76, 0, 0.24, 1], delay: 0.05 }}
        />
      )}
    </MotionConfig>
  );
}
