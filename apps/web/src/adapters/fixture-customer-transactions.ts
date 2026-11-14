/**
 * Labeled fixture customer transactions.
 * No case-api route exists; real-peers must show unavailable — never invent live rows.
 */
export type FixtureCustomerTransaction = {
  transaction_ref: string;
  order_reference: string;
  amount_minor: number;
  currency: "INR";
  status: string;
  occurred_at: string;
};

export const FIXTURE_CUSTOMER_TRANSACTIONS: FixtureCustomerTransaction[] = [
  {
    transaction_ref: "txn-demo-1001",
    order_reference: "ord-demo-55",
    amount_minor: 150000,
    currency: "INR",
    status: "CAPTURED",
    occurred_at: "2026-11-10T09:15:00Z",
  },
  {
    transaction_ref: "txn-demo-1002",
    order_reference: "ord-demo-56",
    amount_minor: 42000,
    currency: "INR",
    status: "FAILED",
    occurred_at: "2026-11-11T14:02:00Z",
  },
];

/** Merchant portal transaction explorer — no list peer; fixture only. */
export type FixtureMerchantTransaction = {
  transaction_ref: string;
  order_reference: string;
  amount_minor: number;
  currency: "INR";
  status: string;
  occurred_at: string;
};

export const FIXTURE_MERCHANT_TRANSACTIONS: FixtureMerchantTransaction[] = [
  {
    transaction_ref: "txn-m-2001",
    order_reference: "ord-m-901",
    amount_minor: 250000,
    currency: "INR",
    status: "CAPTURED",
    occurred_at: "2026-11-12T08:00:00Z",
  },
  {
    transaction_ref: "txn-m-2002",
    order_reference: "ord-m-902",
    amount_minor: 9900,
    currency: "INR",
    status: "REFUNDED",
    occurred_at: "2026-11-12T16:30:00Z",
  },
];

/** merchant-refunds has GET-by-id only — no list route. Fixture list for portal. */
export type FixtureRefundRequest = {
  request_id: string;
  transaction_ref: string;
  amount_minor: number;
  currency: "INR";
  status: string;
};

export const FIXTURE_MERCHANT_REFUNDS: FixtureRefundRequest[] = [
  {
    request_id: "refund-req-demo-1",
    transaction_ref: "txn-m-2002",
    amount_minor: 9900,
    currency: "INR",
    status: "SUBMITTED",
  },
];
