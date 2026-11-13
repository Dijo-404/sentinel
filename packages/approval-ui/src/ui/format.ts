/** Format integer minor units for display without inventing floats in authority paths. */
export function formatMinorUnits(amountMinor: number, currency: "INR"): string {
  const major = Math.trunc(amountMinor / 100);
  const minor = Math.abs(amountMinor % 100)
    .toString()
    .padStart(2, "0");
  return `${currency} ${major}.${minor} (${amountMinor} minor)`;
}

export function formatAgeSeconds(ageSeconds: number): string {
  if (ageSeconds < 60) {
    return `${ageSeconds}s`;
  }
  const minutes = Math.floor(ageSeconds / 60);
  const seconds = ageSeconds % 60;
  if (minutes < 60) {
    return `${minutes}m ${seconds}s`;
  }
  const hours = Math.floor(minutes / 60);
  const remMinutes = minutes % 60;
  return `${hours}h ${remMinutes}m`;
}
