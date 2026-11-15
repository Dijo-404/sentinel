"use client";

import { useState } from "react";
import type { ApprovalSlotProps } from "@/application/ports";
import { StatusChip } from "@/components/status-chip";
import { MaskedRef } from "@/components/masked-ref";
import { labelActionStatus } from "@/domain/status-labels";
import { maskProviderRef, maskTransactionRef, formatAmountMinor } from "@/domain/mask";
import { PeerError } from "@/domain/types";

/**
 * Local approval-ui.v1 substitute. Not the SN-013 package.
 * Slot boundary only — financial authority stays server-side via decide().
 * Digest, case revision, and decision expiry are displayed and submitted exactly.
 */
export function LocalApprovalSubstitute(props: ApprovalSlotProps) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const actionLabel = labelActionStatus(props.action.status);

  async function submit(decision: "APPROVE" | "REJECT") {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const approval = await props.decide(props.action.action_id, {
        decision,
        action_digest: props.action.action_digest,
        case_revision: props.caseRecord.revision,
        policy_version: props.action.payload.policy_version,
        expires_at: props.decisionExpiresAt,
      });
      setMessage(`Decision recorded: ${approval.decision} (${approval.approval_id})`);
      props.onRefresh?.();
    } catch (err) {
      const text =
        err instanceof PeerError
          ? `${err.code}: ${err.message}`
          : err instanceof Error
            ? err.message
            : "Decision failed";
      if (err instanceof PeerError && err.code.includes("CONFLICT")) {
        props.onConflict?.(text);
      }
      setError(text);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="slot-box"
      data-testid="approval-slot"
      data-slot="approval-ui.v1-local"
      aria-labelledby="approval-slot-title"
    >
      <h2 id="approval-slot-title">Approval slot (local substitute)</h2>
      <p className="muted">
        Embedded substitute for approval-ui.v1. Real package selected at assembly.
      </p>
      <div className="row">
        <StatusChip label={actionLabel} />
        <MaskedRef
          label="transaction"
          masked={maskTransactionRef(props.action.payload.transaction_ref)}
        />
        <MaskedRef label="provider" masked={maskProviderRef(props.action.provider_ref)} />
        <span className="mono" data-testid="approval-amount">
          {formatAmountMinor(props.action.payload.amount_minor, props.action.payload.currency)}
        </span>
      </div>
      <dl className="approval-facts" data-testid="approval-exact-facts">
        <div>
          <dt>Case revision</dt>
          <dd data-testid="approval-case-revision">{props.caseRecord.revision}</dd>
        </div>
        <div>
          <dt>Action digest</dt>
          <dd data-testid="approval-action-digest">
            <code className="mono">{props.action.action_digest}</code>
          </dd>
        </div>
        <div>
          <dt>Policy version</dt>
          <dd data-testid="approval-policy-version">{props.action.payload.policy_version}</dd>
        </div>
        <div>
          <dt>Decision expiry</dt>
          <dd data-testid="approval-decision-expires-at">{props.decisionExpiresAt}</dd>
        </div>
      </dl>
      <div className="row" style={{ marginTop: "0.75rem" }}>
        <button
          type="button"
          data-testid="approval-approve"
          disabled={busy}
          onClick={() => void submit("APPROVE")}
        >
          Approve
        </button>
        <button
          type="button"
          className="secondary"
          data-testid="approval-reject"
          disabled={busy}
          onClick={() => void submit("REJECT")}
        >
          Reject
        </button>
      </div>
      {message ? <p role="status">{message}</p> : null}
      {error ? (
        <p role="alert" data-testid="approval-slot-error">
          {error}
        </p>
      ) : null}
    </section>
  );
}
