/** Rolling UTC metrics window derived at request time — not a fixed fixture calendar. */

export function rollingMetricsWindow(
  now: Date = new Date(),
  dayCount = 14,
): { window_start: string; window_end: string } {
  const end = Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate(),
    23,
    59,
    59,
  );
  const start = end - (Math.max(dayCount, 1) - 1) * 86_400_000;
  const startDay = new Date(start);
  startDay.setUTCHours(0, 0, 0, 0);
  return {
    window_start: startDay.toISOString().replace(/\.\d{3}Z$/, "Z"),
    window_end: new Date(end).toISOString().replace(/\.\d{3}Z$/, "Z"),
  };
}
