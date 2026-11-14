"use client";

import { useShell } from "@/adapters/shell-context";
import { FIXTURE_CUSTOMER_TRANSACTIONS } from "@/adapters/fixture-customer-transactions";
import { formatAmountMinor, maskTransactionRef } from "@/domain/mask";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

/**
 * No case-api customer transaction list exists.
 * Fixture: labeled demo rows. Real-peers: fail closed — never invent live data.
 */
export default function CustomerTransactionsPage() {
  const { config } = useShell();

  if (config.mode === "real-peers") {
    return (
      <div className="panel stack" data-testid="customer-transactions">
        <h1>Transactions</h1>
        <UiState
          tone="empty"
          title="Transactions unavailable"
          detail="No customer transaction list peer is wired (GET /v1/customer/transactions does not exist on case-api). Live rows are withheld — not synthetic stand-ins."
        />
      </div>
    );
  }

  return (
    <div className="panel stack" data-testid="customer-transactions">
      <h1>Transactions</h1>
      <p className="muted">
        Fixture transaction list — not live payment data. No case-api route
        exists for customer transactions.
      </p>
      <FixtureBanner />
      <table className="table" aria-label="Fixture customer transactions">
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
          {FIXTURE_CUSTOMER_TRANSACTIONS.map((row) => (
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
