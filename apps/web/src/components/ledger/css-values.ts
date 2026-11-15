/**
 * Percent string rounded to 2 decimals. Browsers re-serialize inline CSS at lower
 * precision, so raw floats make server HTML and client props disagree (hydration error).
 */
export function pct(n: number): string {
  return `${Math.round(n * 100) / 100}%`;
}
