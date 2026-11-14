"use client";

import { motion, useReducedMotion } from "framer-motion";

type Props = {
  /** 0..1 */
  value: number;
  label: string;
  caption?: string;
  size?: number;
};

/** Ring gauge for a single ratio (e.g. verified within SLA). */
export function RadialGauge({ value, label, caption, size = 140 }: Props) {
  const reduce = useReducedMotion();
  const r = 44;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(1, value));
  const pct = Math.round(clamped * 100);

  return (
    <figure className="gauge" style={{ width: size }}>
      <svg
        viewBox="0 0 100 100"
        width={size}
        height={size}
        role="img"
        aria-label={`${label}: ${pct}%`}
      >
        <circle cx="50" cy="50" r={r} className="gauge__track" />
        <motion.circle
          cx="50"
          cy="50"
          r={r}
          className="gauge__fill"
          strokeDasharray={c}
          initial={reduce ? false : { strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - clamped) }}
          transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
          transform="rotate(-90 50 50)"
        />
        <text x="50" y="52" className="gauge__value" textAnchor="middle">
          {pct}%
        </text>
      </svg>
      <figcaption>
        <span className="gauge__label">{label}</span>
        {caption ? <span className="gauge__caption">{caption}</span> : null}
      </figcaption>
    </figure>
  );
}
