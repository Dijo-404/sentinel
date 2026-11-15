export type WaterfallStep = { label: string; value: number; kind: "total" | "delta"; color: string };

/** Running-balance geometry. Totals start at 0; deltas float from the running balance. Pure. */
export function computeWaterfall(steps: WaterfallStep[]) {
  let run = 0;
  const geo = steps.map((s) => {
    if (s.kind === "total") {
      run = s.value;
      return { ...s, base: 0, size: s.value };
    }
    const before = run;
    run += s.value;
    return { ...s, base: Math.min(before, run), size: Math.abs(s.value) };
  });
  const max = Math.max(1, ...geo.map((g) => g.base + g.size));
  return { geo, max, end: run };
}

export function Waterfall({ steps, format, height = 240, caption }: { steps: WaterfallStep[]; format: (v: number) => string; height?: number; caption: string }) {
  const { geo, max } = computeWaterfall(steps);
  return (
    <div className="lk-waterfall" style={{ height }} role="img" aria-label={caption}>
      {geo.map((g, i) => (
        <div className="lk-waterfall__col" key={g.label}>
          <div className="lk-waterfall__track">
            <span
              className="lk-waterfall__bar"
              style={{
                bottom: `${(g.base / max) * 100}%`,
                height: `${(g.size / max) * 100}%`,
                background: g.color,
                animation: `ledger-rise .7s var(--ease-ledger) ${i * 90}ms both`,
              }}
            />
            <span className="lk-waterfall__val tnum" style={{ bottom: `calc(${((g.base + g.size) / max) * 100}% + 4px)` }}>
              {g.kind === "delta" && g.value < 0 ? "−" : ""}
              {format(Math.abs(g.value))}
            </span>
          </div>
          <span className="lk-waterfall__name">{g.label}</span>
        </div>
      ))}
    </div>
  );
}
