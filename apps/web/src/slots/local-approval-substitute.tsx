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
      const expires = new Date(Date.now() + 15 * 60 * 1000).toISOString();
      const approval = await props.decide(props.action.action_id, {
        decision,
        action_digest: props.action.action_digest,
        case_revision: props.caseRecord.revision,
        policy_version: props.action.payload.policy_version,
        expires_at: expires,
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
        <MaskedRef
          label="provider"
          masked={maskProviderRef(props.action.provider_ref)}
        />
        <span className="mono">
          {formatAmountMinor(
            props.action.payload.amount_minor,
            props.action.payload.currency,
          )}
        </span>
      </div>
      <div className="row" style={{ marginTop: "0.75rem" }}>
        <button
          type="button"
          disabled={busy}
          onClick={() => void submit("APPROVE")}
        >
          Approve
        </button>
        <button
          type="button"
          className="secondary"
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
