type Entry = { name?: string; value?: number | string; color?: string };

type Props = {
  active?: boolean;
  label?: string | number;
  payload?: Entry[];
  format?: (v: number) => string;
};

/** Recharts tooltip in Sentinel chrome. Pass as `content={<ChartTooltip />}`. */
export function ChartTooltip({ active, label, payload, format }: Props) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip__label">{label}</p>
      {payload.map((p) => (
        <p key={String(p.name)} className="chart-tooltip__row">
          <span
            className="chart-tooltip__swatch"
            style={{ background: p.color }}
          />
          <span>{p.name}</span>
          <strong className="tnum">
            {format && typeof p.value === "number" ? format(p.value) : p.value}
          </strong>
        </p>
      ))}
    </div>
  );
}
