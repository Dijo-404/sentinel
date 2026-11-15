"use client";

import { useId } from "react";
import { motion, useReducedMotion } from "framer-motion";

type Props = {
  values: number[];
  /** Accessible summary; omit when a sibling already states the value. */
  label?: string;
  width?: number;
  height?: number;
  tone?: "primary" | "periwinkle" | "on-dark";
};

const STROKE: Record<NonNullable<Props["tone"]>, string> = {
  primary: "var(--viz-1)",
  periwinkle: "var(--viz-2)",
  "on-dark": "var(--on-dark)",
};

/** Smooth SVG trend line with a soft area fill. Display-only. */
export function Sparkline({ values, label, width = 120, height = 36, tone = "primary" }: Props) {
  const id = useId();
  const reduce = useReducedMotion();
  if (values.length < 2) return null;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pad = 2;
  const pts = values.map((v, i) => [
    (i / (values.length - 1)) * width,
    pad + (1 - (v - min) / span) * (height - pad * 2),
  ]);
  const line = pts
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");
  const area = `${line} L${width},${height} L0,${height} Z`;
  const stroke = STROKE[tone];

  return (
    <svg
      className="sparkline"
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.28" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${id})`} />
      <motion.path
        d={line}
        fill="none"
        stroke={stroke}
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={reduce ? false : { pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
      />
    </svg>
  );
}
