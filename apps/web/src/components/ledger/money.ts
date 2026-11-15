/** ISO 4217 currencies whose minor unit is not 1/100. */
const MINOR_DIGITS: Record<string, number> = { JPY: 0, KRW: 0, BHD: 3, KWD: 3 };

/**
 * Integer minor units + explicit currency → display string.
 * INR uses Indian grouping (₹1,28,450.00); everything else en-US.
 */
export function formatMoney(
  minor: number,
  currency: string,
  opts: { compact?: boolean } = {},
): string {
  const digits = MINOR_DIGITS[currency] ?? 2;
  const major = minor / 10 ** digits;
  const locale = currency === "INR" ? "en-IN" : "en-US";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    notation: opts.compact ? "compact" : "standard",
    maximumFractionDigits: opts.compact ? 1 : digits,
    minimumFractionDigits: opts.compact ? 0 : digits,
  }).format(major);
}
