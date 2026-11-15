"use client";

import {
  SANDBOX_EVIDENCE_LABEL,
  SANDBOX_TRANSACTIONS,
} from "@/adapters/sandbox-paytm-catalog";
import { formatAmountMinor } from "@/domain/mask";

/**
 * Sandbox catalog from Paytm/simulator seed pack.
 * No case-api GET /v1/customer/transactions — rows are labeled sandbox evidence only.
 */
export default function CustomerTransactionsPage() {
  return (
    <div className="panel stack" data-testid="customer-transactions">
      <h1>Transactions</h1>
      <p className="muted" data-testid="sandbox-evidence-label">
        {SANDBOX_EVIDENCE_LABEL}
      </p>
      <table className="table" aria-label="Sandbox customer transactions">
        <thead>
          <tr>
            <th>Transaction</th>
            <th>Order</th>
            <th>Status</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {SANDBOX_TRANSACTIONS.map((row) => (
            <tr key={row.transaction_ref}>
              <td>{row.transaction_ref}</td>
              <td>{row.order_reference}</td>
              <td>{row.status}</td>
              <td className="tnum">{formatAmountMinor(row.amount_minor, row.currency)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
