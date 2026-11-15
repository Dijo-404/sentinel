"use client";

import { useState } from "react";

type Props = {
  rows: string[];
  cols: string[];
  /** values[row][col] */
  values: number[][];
  unit: string;
};

/** Intensity grid (e.g. exceptions by weekday and hour). Hover or focus a cell to read it. */
export function Heatmap({ rows, cols, values, unit }: Props) {
  const max = Math.max(1, ...values.flat());
  const [hover, setHover] = useState<{ r: number; c: number } | null>(null);
  const readout = hover
    ? `${rows[hover.r]} ${cols[hover.c]}: ${values[hover.r]?.[hover.c] ?? 0} ${unit}`
    : `Peak ${max} ${unit}`;

  return (
    <div className="heatmap">
      <p className="heatmap__readout tnum" aria-live="polite">
        {readout}
      </p>
      <div
        className="heatmap__grid"
        style={{ gridTemplateColumns: `3rem repeat(${cols.length}, 1fr)` }}
      >
        <span />
        {cols.map((c) => (
          <span key={c} className="heatmap__col">
            {c}
          </span>
        ))}
        {rows.map((row, r) => (
          <div key={row} className="heatmap__row">
            <span className="heatmap__rowlabel">{row}</span>
            {cols.map((col, c) => {
              const v = values[r]?.[c] ?? 0;
              return (
                <button
                  type="button"
                  key={col}
                  className="heatmap__cell"
                  aria-label={`${row} ${col}: ${v} ${unit}`}
                  style={{
                    backgroundColor: `color-mix(in srgb, var(--viz-1) ${Math.round(
                      8 + (v / max) * 92,
                    )}%, var(--lavender))`,
                  }}
                  onMouseEnter={() => setHover({ r, c })}
                  onFocus={() => setHover({ r, c })}
                  onMouseLeave={() => setHover(null)}
                  onBlur={() => setHover(null)}
                />
              );
            })}
          </div>
        ))}
      </div>
      <div className="heatmap__scale" aria-hidden="true">
        <span>Fewer</span>
        <i />
        <span>More</span>
      </div>
    </div>
  );
}
