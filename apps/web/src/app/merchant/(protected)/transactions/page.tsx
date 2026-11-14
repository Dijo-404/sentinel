"use client";

import { useShell } from "@/adapters/shell-context";
import { FIXTURE_MERCHANT_TRANSACTIONS } from "@/adapters/fixture-customer-transactions";
import { formatAmountMinor, maskTransactionRef } from "@/domain/mask";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

/**
 * No merchant transaction list peer in repo.
 * Fixture: labeled demo rows. Real-peers: fail closed.
 */
export default function MerchantTransactionsPage() {
  const { config } = useShell();

  if (config.mode === "real-peers") {
    return (
      <div className="panel stack" data-testid="merchant-transactions">
        <h1>Transactions</h1>
        <UiState
          tone="empty"
          title="Transactions unavailable"
          detail="No merchant transaction list HTTP route is wired. Live rows are withheld — not synthetic stand-ins."
        />
      </div>
    );
  }

  return (
    <div className="panel stack" data-testid="merchant-transactions">
      <h1>Transactions</h1>
      <p className="muted">
        Fixture merchant payment list — not live captures or settlements.
      </p>
      <FixtureBanner />
      <table className="table" aria-label="Fixture merchant transactions">
        <thead>
          <tr>
            <th>Reference</th>
            <th>Order</th>
            <th>Amount</th>
            <th>Status</th>
            <th>When</th>
          </tr>
        </thead>
        <tbody>
          {FIXTURE_MERCHANT_TRANSACTIONS.map((row) => (
            <tr key={row.transaction_ref}>
              <td>{maskTransactionRef(row.transaction_ref)}</td>
              <td>{row.order_reference}</td>
              <td className="tnum">
                {formatAmountMinor(row.amount_minor, row.currency)}
              </td>
              <td>{row.status}</td>
              <td>{row.occurred_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
