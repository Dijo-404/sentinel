"use client";

import dynamic from "next/dynamic";
import { useReducedMotion } from "framer-motion";
import { useRef, useState } from "react";
import { useWebGL } from "@/components/three/use-webgl";

const BarsScene = dynamic(() => import("@/components/three/bars-scene"), {
  ssr: false,
});

export type Bar3D = { label: string; value: number };

type Props = {
  bars: Bar3D[];
  /** What the values count, e.g. "cases" or "refunded". */
  unit: string;
  format?: (v: number) => string;
  tone?: "light" | "night";
  height?: number;
};

/**
 * 3D bar chart (WebGL) with every value labelled. Axis labels are buttons, so the
 * chart is readable by keyboard and screen reader; falls back to flat bars without WebGL.
 */
export function Bars3D({
  bars,
  unit,
  format = String,
  tone = "light",
  height = 280,
}: Props) {
  const webgl = useWebGL();
  const reduced = Boolean(useReducedMotion());
  const [active, setActive] = useState<number | null>(null);
  const labelRefs = useRef<(HTMLElement | null)[]>([]);
  const max = Math.max(1, ...bars.map((b) => b.value));
  const total = bars.reduce((a, b) => a + b.value, 0);
  const shown = active === null ? null : bars[active];
  const tickRefs = useRef<(HTMLElement | null)[]>([]);

  const ticks = bars.map((b, i) => (
    <button
      type="button"
      key={b.label}
      ref={(el) => {
        tickRefs.current[i] = el;
      }}
      className={webgl ? "bars3d__tick bars3d__tick--float" : "bars3d__tick"}
      aria-pressed={active === i}
      aria-label={`${b.label}: ${format(b.value)} ${unit}`}
      onMouseEnter={() => setActive(i)}
      onMouseLeave={() => setActive(null)}
      onFocus={() => setActive(i)}
      onBlur={() => setActive(null)}
    >
      {b.label}
    </button>
  ));

  return (
    <div className="bars3d" data-tone={tone}>
      <p className="bars3d__readout" aria-live="polite">
        <span className="bars3d__readout-value tnum">
          {format(shown ? shown.value : total)}
        </span>
        <span className="bars3d__readout-label">
          {shown ? `${unit}, ${shown.label}` : `${unit} in total`}
        </span>
      </p>
      <div
        className="bars3d__stage"
        style={{ height }}
        data-cursor={webgl ? "Hover a bar" : undefined}
      >
        {webgl ? (
          <>
            <BarsScene
              bars={bars}
              active={active}
              onActive={setActive}
              tone={tone}
              reduced={reduced}
              labelRefs={labelRefs}
              tickRefs={tickRefs}
            />
            {ticks}
            {bars.map((b, i) => (
              <span
                key={b.label}
                ref={(el) => {
                  labelRefs.current[i] = el;
                }}
                className="bars3d__value tnum"
                data-active={active === i || undefined}
                aria-hidden="true"
              >
                {format(b.value)}
              </span>
            ))}
          </>
        ) : (
          <div
            className="bars3d__flat"
            style={{ gridTemplateColumns: `repeat(${bars.length}, 1fr)` }}
            aria-hidden="true"
          >
            {bars.map((b, i) => (
              <div
                key={b.label}
                className="bars3d__flat-col"
                data-active={active === i || undefined}
              >
                <span className="bars3d__flat-value tnum">
                  {format(b.value)}
                </span>
                <i style={{ height: `${(b.value / max) * 100}%` }} />
              </div>
            ))}
          </div>
        )}
      </div>
      {webgl ? null : (
        <div
          className="bars3d__axis"
          style={{ gridTemplateColumns: `repeat(${bars.length}, 1fr)` }}
        >
          {ticks}
        </div>
      )}
    </div>
  );
}
