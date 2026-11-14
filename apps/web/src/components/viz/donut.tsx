"use client";

import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export type Slice = { name: string; value: number };

const COLORS = [
  "var(--viz-1)",
  "var(--viz-2)",
  "var(--viz-3)",
  "var(--viz-4)",
  "var(--viz-5)",
];

type Props = {
  slices: Slice[];
  /** Center caption under the total. */
  centerLabel?: string;
  height?: number;
};

/** Donut with an interactive legend: hover or focus a row to isolate a slice. */
export function Donut({ slices, centerLabel = "Total", height = 220 }: Props) {
  const [active, setActive] = useState<number | null>(null);
  const total = slices.reduce((a, s) => a + s.value, 0);
  const shown = active === null ? null : slices[active];
  // Zero slices stay in the legend but draw no sector (avoids hairline ticks).
  const visible = slices
    .map((s, index) => ({ ...s, index }))
    .filter((s) => s.value > 0);

  if (total === 0) {
    return <p className="viz-empty">No cases in scope yet.</p>;
  }

  return (
    <div className="donut">
      <div className="donut__chart" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={visible}
              dataKey="value"
              nameKey="name"
              innerRadius="62%"
              outerRadius="92%"
              paddingAngle={visible.length > 1 ? 2 : 0}
              stroke="none"
              onMouseLeave={() => setActive(null)}
              onMouseEnter={(_, i) => setActive(visible[i]?.index ?? null)}
            >
              {visible.map((s) => (
                <Cell
                  key={s.name}
                  fill={COLORS[s.index % COLORS.length]}
                  opacity={active === null || active === s.index ? 1 : 0.28}
                />
              ))}
            </Pie>
            <Tooltip content={() => null} />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut__center" aria-hidden="true">
          <span className="donut__total tnum">{shown?.value ?? total}</span>
          <span className="donut__caption">{shown?.name ?? centerLabel}</span>
        </div>
      </div>
      <ul className="donut__legend">
        {slices.map((s, i) => (
          <li key={s.name}>
            <button
              type="button"
              className="donut__key"
              data-active={active === i || undefined}
              onMouseEnter={() => setActive(i)}
              onMouseLeave={() => setActive(null)}
              onFocus={() => setActive(i)}
              onBlur={() => setActive(null)}
            >
              <span
                className="donut__swatch"
                style={{ background: COLORS[i % COLORS.length] }}
                aria-hidden="true"
              />
              {/* Single text node so legend text never equals a bare KPI label. */}
              <span className="donut__name">{`${s.name} (${s.value})`}</span>
              <span className="donut__pct tnum">
                {Math.round((s.value / total) * 100)}%
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
