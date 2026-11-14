"use client";

import { UiState } from "@/components/ui-states";

/**
 * No merchant transaction list peer in repo.
 * Never invent rows — seed/DB path requires a real list API first.
 */
export default function MerchantTransactionsPage() {
  return (
    <div className="panel stack" data-testid="merchant-transactions">
      <h1>Transactions</h1>
      <UiState
        tone="error"
        title="Transactions unavailable"
        detail="No merchant transaction list HTTP route is wired. Live or seeded rows are withheld — not synthetic stand-ins."
      />
    </div>
  );
}
