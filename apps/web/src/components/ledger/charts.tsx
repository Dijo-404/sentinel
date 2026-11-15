"use client";

import { useState, type ReactNode } from "react";

/* Small SVG charts shared by every surface. Each pure path builder is exported for tests. */

/** Polyline path over a 0..w × 0..h box, auto-scaled to `max` (default: series max × 1.1). */
export function linePath(values: number[], w: number, h: number, max = Math.max(1, ...values) * 1.1): string {
  const n = values.length;
  return values.map((v, i) => `${i ? "L" : "M"}${((i / Math.max(1, n - 1)) * w).toFixed(1)} ${(h - (v / max) * h).toFixed(1)}`).join(" ");
}

/** Stacked areas, bottom layer first. Returns one closed path per layer. Pure. */
export function stackPaths(layers: number[][], w: number, h: number): string[] {
  const n = layers[0]?.length ?? 0;
  const tops: number[][] = [];
  layers.forEach((l, li) => tops.push(l.map((v, i) => v + (li ? tops[li - 1][i] : 0))));
  const max = Math.max(1, ...(tops[tops.length - 1] ?? [1])) * 1.05;
  const X = (i: number) => ((i / Math.max(1, n - 1)) * w).toFixed(1);
  const Y = (v: number) => (h - (v / max) * h).toFixed(1);
  return tops.map((top, li) => {
    const bottom = li ? tops[li - 1] : Array(n).fill(0);
    const up = top.map((v, i) => `${i ? "L" : "M"}${X(i)} ${Y(v)}`).join(" ");
    const down = [...bottom].reverse().map((v, k) => `L${X(n - 1 - k)} ${Y(v)}`).join(" ");
    return `${up} ${down} Z`;
  });
}

export function Sparkline({ values, color = "var(--signal)", height = 30, area = true }: { values: number[]; color?: string; height?: number; area?: boolean }) {
  const d = linePath(values, 120, height);
  return (
    <svg viewBox={`0 0 120 ${height}`} width="100%" height={height} preserveAspectRatio="none" aria-hidden="true">
      {area && <path d={`${d} L120 ${height} L0 ${height} Z`} fill={color} opacity={0.12} />}
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function StreamArea({ layers, colors, height = 160 }: { layers: number[][]; colors: string[]; height?: number }) {
  const paths = stackPaths(layers, 400, height);
  return (
    <svg viewBox={`0 0 400 ${height}`} width="100%" height={height} preserveAspectRatio="none" aria-hidden="true">
      {paths.map((d, i) => (
        <path key={i} d={d} fill={colors[i]} opacity={0.5} style={{ transition: "d .8s linear" }} />
      ))}
    </svg>
  );
}

export type Ring = { label: string; value: number; color: string };

export function RingStack({ rings, size = 150 }: { rings: Ring[]; size?: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
      <svg viewBox="0 0 120 120" width={size} height={size} aria-hidden="true" style={{ transform: "rotate(-90deg)" }}>
        {rings.map((r, i) => {
          const rad = 52 - i * 14;
          const c = 2 * Math.PI * rad;
          return (
            <g key={r.label}>
              <circle cx={60} cy={60} r={rad} fill="none" stroke="var(--line)" strokeWidth={9} />
              <circle cx={60} cy={60} r={rad} fill="none" stroke={r.color} strokeWidth={9} strokeLinecap="round" strokeDasharray={`${(r.value * c).toFixed(1)} ${c.toFixed(1)}`} style={{ transition: "stroke-dasharray .8s var(--ease-ledger)" }} />
            </g>
          );
        })}
      </svg>
      <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 8, fontSize: 13 }}>
        {rings.map((r) => (
          <li key={r.label}>
            <strong className="display tnum" style={{ color: r.color, fontSize: 20 }}>{Math.round(r.value * 100)}%</strong> {r.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Area chart with crosshair. Two series: primary (signal) and secondary (verified). */
export function HoverArea({
  primary,
  secondary,
  labels,
  height = 240,
  render,
  caption,
}: {
  primary: number[];
  secondary?: number[];
  labels: string[];
  height?: number;
  render: (i: number) => ReactNode;
  caption: string;
}) {
  const [hi, setHi] = useState(primary.length - 1);
  const W = 800;
  const max = Math.max(1, ...primary) * 1.15;
  const X = (i: number) => (i / Math.max(1, primary.length - 1)) * W;
  const Y = (v: number) => height - (v / max) * (height - 12);
  const d1 = linePath(primary, W, height - 12, max);
  const d2 = secondary ? linePath(secondary, W, height - 12, max) : "";
  return (
    <div className="lk-chart">
      <div className="lk-chart__head">{render(hi)}</div>
      <svg
        viewBox={`0 0 ${W} ${height}`}
        width="100%"
        height={height}
        role="img"
        aria-label={caption}
        style={{ cursor: "crosshair" }}
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          setHi(Math.max(0, Math.min(primary.length - 1, Math.round(((e.clientX - r.left) / r.width) * (primary.length - 1)))));
        }}
        onMouseLeave={() => setHi(primary.length - 1)}
      >
        <defs>
          <linearGradient id="lk-area-a" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="var(--viz-1)" stopOpacity=".45" />
            <stop offset="1" stopColor="var(--viz-1)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1={0} x2={W} y1={height * f} y2={height * f} stroke="var(--line)" />
        ))}
        <path d={`${d1} L${W} ${height} L0 ${height} Z`} fill="url(#lk-area-a)" />
        <path d={d1} fill="none" stroke="var(--viz-1)" strokeWidth={2.5} style={{ strokeDasharray: 1600, animation: "ledger-draw 2.4s var(--ease-ledger) both" }} />
        {d2 && <path d={d2} fill="none" stroke="var(--viz-ok)" strokeWidth={1.8} />}
        <line x1={X(hi)} x2={X(hi)} y1={0} y2={height} stroke="var(--line-strong)" strokeDasharray="3 3" />
        <circle cx={X(hi)} cy={Y(primary[hi])} r={6} fill="var(--canvas)" stroke="var(--viz-1)" strokeWidth={2.5} />
        {secondary && <circle cx={X(hi)} cy={Y(secondary[hi])} r={4} fill="var(--viz-ok)" />}
      </svg>
      <div className="lk-axis">
        <span>{labels[0]}</span>
        <span>{labels[Math.floor(labels.length / 2)]}</span>
        <span>{labels[labels.length - 1]}</span>
      </div>
    </div>
  );
}

export function CohortGrid({ rows, cols }: { rows: { label: string; cells: (number | null)[] }[]; cols: string[] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <div className="lk-cohort" style={{ gridTemplateColumns: `72px repeat(${cols.length}, minmax(44px, 1fr))`, minWidth: 480 }}>
        <span />
        {cols.map((c) => (
          <span key={c} style={{ color: "var(--fog)", minHeight: 0 }}>{c}</span>
        ))}
        {rows.map((r) => (
          <CohortRow key={r.label} row={r} />
        ))}
      </div>
    </div>
  );
}

function CohortRow({ row }: { row: { label: string; cells: (number | null)[] } }) {
  return (
    <>
      <span style={{ color: "var(--fog)", justifyContent: "start" }}>{row.label}</span>
      {row.cells.map((v, i) => {
        if (v === null) return <span key={i} />;
        const first = i === 0;
        const a = first ? 0.9 : Math.min(0.9, v / 22);
        return (
          <span
            key={i}
            data-cell
            title={`${row.label}, week ${i}: ${v}%`}
            style={{ background: first ? "var(--lavender)" : `rgba(255,138,92,${(0.1 + a * 0.8).toFixed(2)})`, color: a > 0.5 && !first ? "#07070c" : "var(--ink-secondary)" }}
          >
            {v}%
          </span>
        );
      })}
    </>
  );
}
