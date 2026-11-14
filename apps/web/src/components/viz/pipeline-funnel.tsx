"use client";

import { motion, useReducedMotion } from "framer-motion";

export type Stage = { key: string; label: string; count: number };

type Props = {
  stages: Stage[];
  /** Stage to emphasise (e.g. waiting approval). */
  highlight?: string;
};

/** Ordered stage bars; width is share of the largest stage. */
export function PipelineFunnel({ stages, highlight }: Props) {
  const reduce = useReducedMotion();
  const max = Math.max(1, ...stages.map((s) => s.count));
  return (
    <ol className="funnel">
      {stages.map((s, i) => (
        <li
          key={s.key}
          className="funnel__row"
          data-highlight={s.key === highlight || undefined}
        >
          <span className="funnel__step tnum" aria-hidden="true">
            {i + 1}
          </span>
          <span className="funnel__label">{s.label}</span>
          <span className="funnel__track">
            <motion.span
              className="funnel__bar"
              initial={reduce ? false : { scaleX: 0 }}
              animate={{ scaleX: s.count / max }}
              transition={{
                duration: 0.8,
                delay: reduce ? 0 : i * 0.06,
                ease: [0.22, 1, 0.36, 1],
              }}
            />
          </span>
          <span className="funnel__count tnum">{s.count}</span>
        </li>
      ))}
    </ol>
  );
}
