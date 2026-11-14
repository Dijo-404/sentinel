"use client";

import { UiState } from "@/components/ui-states";

/**
 * No case-api customer transaction list exists.
 * Never invent rows — wire a list peer before showing data.
 */
export default function CustomerTransactionsPage() {
  return (
    <div className="panel stack" data-testid="customer-transactions">
      <h1>Transactions</h1>
      <UiState
        tone="error"
        title="Transactions unavailable"
        detail="No customer transaction list peer is wired (GET /v1/customer/transactions does not exist on case-api). Seeded/live rows are withheld — not synthetic stand-ins."
      />
    </div>
  );
}
