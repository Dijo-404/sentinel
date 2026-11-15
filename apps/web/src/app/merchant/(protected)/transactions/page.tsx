"use client";

import { SANDBOX_EVIDENCE_LABEL, SANDBOX_TRANSACTIONS } from "@/adapters/sandbox-paytm-catalog";
import { formatAmountMinor } from "@/domain/mask";

/**
 * Sandbox catalog from Paytm/simulator seed pack.
 * No merchant transaction list peer — rows are labeled sandbox evidence only.
 */
export default function MerchantTransactionsPage() {
  return (
    <div className="panel stack" data-testid="merchant-transactions">
      <h1>Transactions</h1>
      <p className="muted" data-testid="sandbox-evidence-label">
        {SANDBOX_EVIDENCE_LABEL}
      </p>
      <div className="table-scroll" role="region" aria-label="Scrollable transactions" tabIndex={0}>
        <table className="table" aria-label="Sandbox merchant transactions">
          <thead>
            <tr>
              <th>Transaction</th>
              <th>Order</th>
              <th>Merchant</th>
              <th>Status</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {SANDBOX_TRANSACTIONS.map((row) => (
              <tr key={row.transaction_ref}>
                <td>{row.transaction_ref}</td>
                <td>{row.order_reference}</td>
                <td>{row.merchant_ref}</td>
                <td>{row.status}</td>
                <td className="tnum">{formatAmountMinor(row.amount_minor, row.currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
