"use client";

import { useState } from "react";
import { pct } from "./css-values";

export type BarSeries = { key: string; label: string; color: string };
export type BarRow = {
  label: string;
  values: Record<string, number>;
  line?: number;
  prevLine?: number;
};

type Props = {
  series: BarSeries[];
  rows: BarRow[];
  height?: number;
  /** Max for the overlay line's own scale (e.g. 5 for a 0–5% rate). */
  lineMax?: number;
  lineLabel?: string;
  showPrev?: boolean;
  onHover?: (index: number | null) => void;
  caption: string;
};

/** Stacked bars with a togglable legend, hover isolation, optional rate line and a data-table fallback. */
export function StackedBars({
  series,
  rows,
  height = 260,
  lineMax = 5,
  lineLabel,
  showPrev,
  onHover,
  caption,
}: Props) {
  const [off, setOff] = useState<Record<string, boolean>>({});
  const [hi, setHi] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const live = series.filter((s) => !off[s.key]);
  const max =
    Math.max(1, ...rows.map((r) => series.reduce((a, s) => a + (r.values[s.key] ?? 0), 0))) * 1.1;
  const n = rows.length;
  const linePath = (pick: (r: BarRow) => number | undefined) =>
    rows
      .map((r, i) => {
        const v = pick(r);
        return v === undefined
          ? ""
          : `${i ? "L" : "M"}${(((i + 0.5) / n) * 1000).toFixed(1)} ${(height - (v / lineMax) * (height - 20)).toFixed(1)}`;
      })
      .join(" ");
  const hover = (i: number | null) => {
    setHi(i);
    onHover?.(i);
  };

  return (
    <div className="lk-chart">
      <ul className="lk-legend">
        {series.map((s) => (
          <li key={s.key}>
            <button
              type="button"
              aria-pressed={!off[s.key]}
              onClick={() => setOff({ ...off, [s.key]: !off[s.key] })}
            >
              <i style={{ background: s.color }} />
              {s.label}
            </button>
          </li>
        ))}
        {lineLabel && (
          <li style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "var(--ok)" }}>
            <i style={{ width: 14, height: 2, background: "var(--ok)" }} />
            {lineLabel}
          </li>
        )}
      </ul>
      {table ? (
        <table className="lk-data-table">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr>
              <th scope="col">Period</th>
              {series.map((s) => (
                <th key={s.key} scope="col">
                  {s.label}
                </th>
              ))}
              {lineLabel && <th scope="col">{lineLabel}</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label}>
                <th scope="row">{r.label}</th>
                {series.map((s) => (
                  <td key={s.key} className="tnum">
                    {r.values[s.key] ?? 0}
                  </td>
                ))}
                {lineLabel && <td className="tnum">{r.line?.toFixed(1)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div
          className="lk-bars"
          style={{ height, gap: n > 20 ? 3 : 8 }}
          data-hovering={hi !== null || undefined}
          onMouseLeave={() => hover(null)}
          role="img"
          aria-label={caption}
        >
          {rows.map((r, i) => (
            <div
              key={r.label}
              className="lk-bars__col"
              data-active={hi === i || undefined}
              onMouseEnter={() => hover(i)}
              style={{ animation: `ledger-rise .6s var(--ease-ledger) ${i * 15}ms both` }}
            >
              {[...live].reverse().map((s) => (
                <span
                  key={s.key}
                  style={{
                    height: pct(((r.values[s.key] ?? 0) / max) * 100),
                    background: s.color,
                  }}
                />
              ))}
            </div>
          ))}
          {rows.some((r) => r.line !== undefined) && (
            <svg
              className="lk-bars__overlay"
              viewBox={`0 0 1000 ${height}`}
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <path
                d={linePath((r) => r.line)}
                fill="none"
                stroke="var(--ok)"
                strokeWidth={2.5}
                vectorEffect="non-scaling-stroke"
              />
              {showPrev && (
                <path
                  d={linePath((r) => r.prevLine)}
                  fill="none"
                  stroke="var(--ok)"
                  strokeWidth={1.5}
                  strokeDasharray="5 5"
                  opacity={0.45}
                  vectorEffect="non-scaling-stroke"
                />
              )}
            </svg>
          )}
        </div>
      )}
      <div className="lk-axis">
        <span>{rows[0]?.label}</span>
        <span>{rows[Math.floor(n / 2)]?.label}</span>
        <span>{rows[n - 1]?.label}</span>
      </div>
      <button
        type="button"
        className="lk-table-toggle"
        onClick={() => setTable(!table)}
        aria-pressed={table}
      >
        {table ? "Show chart" : "Show as table"}
      </button>
    </div>
  );
}
