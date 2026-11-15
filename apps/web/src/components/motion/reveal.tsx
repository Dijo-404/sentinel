"use client";

import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

const EASE = [0.22, 1, 0.36, 1] as const;

/** Rise-in on first view. Reduced motion is handled globally by MotionConfig/CSS. */
export function Reveal({
  children,
  delay = 0,
  className,
  as = "div",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: "div" | "section" | "li";
}) {
  const C = motion[as];
  const reduce = useReducedMotion();
  return (
    <C
      className={className}
      data-reveal
      initial={reduce ? false : { opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: reduce ? 0 : 0.35, delay: reduce ? 0 : delay, ease: EASE }}
    >
      {children}
    </C>
  );
}

/** Headline that rises word by word from a mask. */
export function MaskHeadline({
  text,
  accentFrom,
  className,
}: {
  text: string;
  accentFrom?: number;
  className?: string;
}) {
  const words = text.split(" ");
  const reduce = useReducedMotion();
  return (
    <h1 className={className} aria-label={text}>
      {words.map((w, i) => (
        <span key={`${w}-${i}`} className="mask-word" aria-hidden="true">
          <motion.span
            style={{
              display: "inline-block",
              color: accentFrom !== undefined && i >= accentFrom ? "var(--ok)" : undefined,
            }}
            initial={reduce ? false : { y: "110%", opacity: 0 }}
            animate={{ y: "0%", opacity: 1 }}
            transition={{
              duration: reduce ? 0 : 0.9,
              delay: reduce ? 0 : 0.1 + i * 0.06,
              ease: EASE,
            }}
          >
            {w}
          </motion.span>
        </span>
      ))}
    </h1>
  );
}
