export type Point = { x: string; y: number };

function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}

/** Synthetic daily values for KPI sparklines / area charts. */
export function dailySeries(days = 14, seed = 42, base = 100): number[] {
  const out: number[] = [];
  let cursor = seed;
  for (let i = 0; i < days; i += 1) {
    cursor = (cursor * 1103515245 + 12345) & 0x7fffffff;
    const wobble = ((cursor % 21) - 10) / 100;
    const trend = i * 1.4;
    out.push(Math.round(clamp(base * (1 + wobble) + trend, 10, 10_000)));
  }
  return out;
}

/** Labeled {x,y} points for Recharts-style series. */
export function labeledSeries(days = 14, seed = 7, base = 80): Point[] {
  const values = dailySeries(days, seed, base);
  return values.map((y, i) => ({
    x: `D${String(i + 1).padStart(2, "0")}`,
    y,
  }));
}

/** Paired volume vs refund request series (display-only). */
export function volumeVsRefunds(days = 14): {
  volume: Point[];
  refundRequests: Point[];
} {
  return {
    volume: labeledSeries(days, 11, 220),
    refundRequests: labeledSeries(days, 29, 18),
  };
}

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/** Fixed simulator "today", so server and client render identical axis labels. */
export const FIXTURE_TODAY = Date.UTC(2026, 10, 13);

/** Calendar labels ("Nov 3") for the `days` days ending at FIXTURE_TODAY. */
export function dateLabels(days: number, end = FIXTURE_TODAY): string[] {
  return Array.from({ length: days }, (_, i) => {
    const d = new Date(end - (days - 1 - i) * 86_400_000);
    return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`;
  });
}

export const fixtureSeries = {
  dailySeries,
  labeledSeries,
  volumeVsRefunds,
  dateLabels,
};
