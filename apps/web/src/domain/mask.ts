/** Mask PII and payment identifiers for UI display. Domain-only; no I/O. */

const KEEP_TAIL = 4;

export function maskReference(raw: string, prefix = "…"): string {
  if (!raw) return prefix;
  if (raw.length <= KEEP_TAIL) return `${prefix}${raw}`;
  return `${prefix}${raw.slice(-KEEP_TAIL)}`;
}

export function maskSubjectRef(subjectRef: string): string {
  return maskReference(subjectRef, "subj-…");
}

export function maskTransactionRef(transactionRef: string): string {
  return maskReference(transactionRef, "txn-…");
}

export function maskProviderRef(providerRef: string): string {
  return maskReference(providerRef, "prov-…");
}

export function maskOrderReference(orderReference: string): string {
  return maskReference(orderReference, "ord-…");
}

export function formatAmountMinor(amountMinor: number, currency: string): string {
  if (!Number.isInteger(amountMinor)) {
    throw new Error("amount_minor must be an integer");
  }
  const major = (amountMinor / 100).toFixed(2);
  return `${currency} ${major}`;
}
