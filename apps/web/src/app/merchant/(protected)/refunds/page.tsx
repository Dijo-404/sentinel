"use client";

import { useShell } from "@/adapters/shell-context";
import { FIXTURE_MERCHANT_REFUNDS } from "@/adapters/fixture-customer-transactions";
import { formatAmountMinor, maskTransactionRef } from "@/domain/mask";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

/**
 * merchant-refunds exposes GET /v1/refund-requests/{id} only — no list route.
 * Fixture: labeled demo rows. Real-peers: fail closed.
 */
export default function MerchantRefundsPage() {
  const { config } = useShell();

  if (config.mode === "real-peers") {
    return (
      <div className="panel stack" data-testid="merchant-refunds">
        <h1>Refund requests</h1>
        <UiState
          tone="empty"
          title="Refund list unavailable"
          detail="merchant-refunds has GET-by-id only (no list). Live list withheld — not synthetic stand-ins. Requests are not ledger credit proof."
        />
      </div>
    );
  }

  return (
    <div className="panel stack" data-testid="merchant-refunds">
      <h1>Refund requests</h1>
      <p className="muted">
        Fixture refund-request list — not provider credit or ledger authority.
        Peer has no list route.
      </p>
      <FixtureBanner />
      <table className="table" aria-label="Fixture refund requests">
        <thead>
          <tr>
            <th>Request</th>
            <th>Transaction</th>
            <th>Amount</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {FIXTURE_MERCHANT_REFUNDS.map((row) => (
            <tr key={row.request_id}>
              <td>{row.request_id}</td>
              <td>{maskTransactionRef(row.transaction_ref)}</td>
              <td className="tnum">
                {formatAmountMinor(row.amount_minor, row.currency)}
              </td>
              <td>{row.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
