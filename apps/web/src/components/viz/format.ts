/** "$842", "$8.8k", "$1.2M": short money labels for axes and tooltips. */
export function usdCompact(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `$${(v / 1_000).toFixed(1)}k`;
  return `$${Math.round(v)}`;
}

/**
 * Fixture series are unitless indexes; this turns one point into dollars per day,
 * sized so 14 days of captured volume lands near the $128,400 KPI.
 */
export const FIXTURE_DOLLARS_PER_POINT = 40;
