/**
 * Labeled sandbox catalog from services/simulator fixtures/paytm_staging seed pack
 * (+ known journey orders). Not live bank credit. Not a silent fixture fallback for
 * an absent peer — pages must caption evidence_label explicitly.
 */

export const SANDBOX_EVIDENCE_LABEL =
  "Sandbox seed (Paytm staging / simulator pack) — not live bank credit";

export type SandboxTransaction = {
  transaction_ref: string;
  order_reference: string;
  amount_minor: number;
  currency: "INR";
  status: string;
  merchant_ref: string;
  subject_ref: string;
};

export type SandboxRefund = {
  request_id: string;
  provider_ref: string;
  transaction_ref: string;
  amount_minor: number;
  currency: "INR";
  status: string;
};

/** Mirrors simulator paytm_staging + journey seed payments. */
export const SANDBOX_TRANSACTIONS: SandboxTransaction[] = [
  {
    transaction_ref: "PAYTM-TXN-A1",
    order_reference: "PAYTM-ORDER-A",
    amount_minor: 1000,
    currency: "INR",
    status: "CAPTURED",
    merchant_ref: "merchant-paytm-staging",
    subject_ref: "subject-paytm-staging",
  },
  {
    transaction_ref: "PAYTM-TXN-A2",
    order_reference: "PAYTM-ORDER-A",
    amount_minor: 1000,
    currency: "INR",
    status: "CAPTURED",
    merchant_ref: "merchant-paytm-staging",
    subject_ref: "subject-paytm-staging",
  },
  {
    transaction_ref: "PAYTM-TXN-MISMATCH",
    order_reference: "PAYTM-ORDER-MISMATCH",
    amount_minor: 1000,
    currency: "INR",
    status: "CAPTURED",
    merchant_ref: "merchant-paytm-staging",
    subject_ref: "subject-paytm-staging",
  },
  {
    transaction_ref: "PAYTM-TXN-FAIL-001",
    order_reference: "PAYTM-ORDER-FAIL-001",
    amount_minor: 1000,
    currency: "INR",
    status: "FAILED",
    merchant_ref: "merchant-paytm-staging",
    subject_ref: "subject-paytm-staging",
  },
  {
    transaction_ref: "TXN-A",
    order_reference: "DEMO-ORDER-42",
    amount_minor: 4200,
    currency: "INR",
    status: "CAPTURED",
    merchant_ref: "merchant-demo-1",
    subject_ref: "subject-demo-42",
  },
  {
    transaction_ref: "TXN-B",
    order_reference: "DEMO-ORDER-42",
    amount_minor: 4200,
    currency: "INR",
    status: "CAPTURED",
    merchant_ref: "merchant-demo-1",
    subject_ref: "subject-demo-42",
  },
];

/** Subject-bound order refs in case-api canonical form `{subject_ref}/{order_reference}`. */
export const SANDBOX_ORDER_REFS: string[] = [
  ...new Set(SANDBOX_TRANSACTIONS.map((t) => `${t.subject_ref}/${t.order_reference}`)),
];

/** Mirrors simulator paytm_staging + refund_pending pack. */
export const SANDBOX_REFUNDS: SandboxRefund[] = [
  {
    request_id: "action-paytm-refund-1",
    provider_ref: "SNT-REF-PAYTM-001",
    transaction_ref: "PAYTM-TXN-A1",
    amount_minor: 500,
    currency: "INR",
    status: "PENDING",
  },
  {
    request_id: "refund-pending-1",
    provider_ref: "refund-pending-1",
    transaction_ref: "TXN-REFUND-PENDING",
    amount_minor: 1000,
    currency: "INR",
    status: "PENDING",
  },
];
