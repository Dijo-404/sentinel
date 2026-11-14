import { Sparkline } from "./sparkline";
import { TrendPill } from "./trend-pill";

type Props = {
  label: string;
  value: string;
  caption?: string;
  /** Optional trend series rendered as a sparkline under the value. */
  series?: number[];
  trend?: {
    value: string;
    direction: "up" | "down" | "flat";
    tone?: "good" | "bad" | "neutral";
  };
};

export function StatBlock({ label, value, caption, series, trend }: Props) {
  return (
    <article className="stat-block" data-testid="stat-block">
      <div className="stat-block__head">
        <p className="stat-block__label">{label}</p>
        {trend ? (
          <TrendPill
            value={trend.value}
            direction={trend.direction}
            tone={trend.tone}
          />
        ) : null}
      </div>
      <p className="stat-block__value tnum">{value}</p>
      {series ? (
        <div className="stat-block__spark">
          <Sparkline values={series} width={220} height={40} />
        </div>
      ) : null}
      {caption ? <p className="stat-block__caption">{caption}</p> : null}
    </article>
  );
}
