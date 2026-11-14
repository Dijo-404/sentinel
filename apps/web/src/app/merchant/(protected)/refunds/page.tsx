"use client";

import { UiState } from "@/components/ui-states";

/**
 * merchant-refunds exposes GET /v1/refund-requests/{id} only — no list route.
 * Never invent rows.
 */
export default function MerchantRefundsPage() {
  return (
    <div className="panel stack" data-testid="merchant-refunds">
      <h1>Refund requests</h1>
      <UiState
        tone="error"
        title="Refund list unavailable"
        detail="merchant-refunds has GET-by-id only (no list). Seeded/live list withheld — not synthetic stand-ins. Requests are not ledger credit proof."
      />
    </div>
  );
}
