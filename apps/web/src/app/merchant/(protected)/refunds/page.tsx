"use client";

import { SANDBOX_EVIDENCE_LABEL, SANDBOX_REFUNDS } from "@/adapters/sandbox-paytm-catalog";
import { formatAmountMinor } from "@/domain/mask";

/**
 * Sandbox refund catalog from Paytm/simulator seed pack.
 * merchant-refunds has GET-by-id only — list is labeled sandbox evidence, not ledger credit.
 */
export default function MerchantRefundsPage() {
  return (
    <div className="panel stack" data-testid="merchant-refunds">
      <h1>Refund requests</h1>
      <p className="muted" data-testid="sandbox-evidence-label">
        {SANDBOX_EVIDENCE_LABEL}. Requests are not ledger credit proof.
      </p>
      <table className="table" aria-label="Sandbox merchant refund requests">
        <thead>
          <tr>
            <th>Request</th>
            <th>Provider ref</th>
            <th>Transaction</th>
            <th>Status</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {SANDBOX_REFUNDS.map((row) => (
            <tr key={row.request_id}>
              <td>{row.request_id}</td>
              <td>{row.provider_ref}</td>
              <td>{row.transaction_ref}</td>
              <td>{row.status}</td>
              <td className="tnum">{formatAmountMinor(row.amount_minor, row.currency)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
