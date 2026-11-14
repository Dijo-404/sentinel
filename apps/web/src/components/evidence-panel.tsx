"use client";

import { useEffect, useMemo, useState } from "react";
import type { CaseClient } from "@/application/ports";
import type { Case, Evidence, EvidenceBundle } from "@/domain/types";
import { PeerError } from "@/domain/types";
import {
  labelCaseStatus,
  labelCredit,
  labelRefundStatus,
} from "@/domain/status-labels";
import {
  formatAmountMinor,
  maskOrderReference,
  maskProviderRef,
  maskSubjectRef,
  maskTransactionRef,
} from "@/domain/mask";
import { StatusChip } from "./status-chip";
import { UiState } from "./ui-states";
import { MaskedRef } from "./masked-ref";
import { ApprovalSlot } from "@/slots/approval-slot";
import type { ApprovalSlotProps } from "@/application/ports";
import { demoAction } from "@/adapters/fixture-case-client";
import { PeerError as SlotPeerError } from "@/domain/types";

type Props = {
  caseId: string;
  caseClient: CaseClient;
  /**
   * Supervisor-only. Operator / legacy ops evidence must leave this false
   * so approve/reject controls stay off those routes.
   */
  enableApproval?: boolean;
  /** Authoritative decision window when enableApproval is set. */
  decisionExpiresAt?: string;
  /** Injected approval slot override for tests (e.g. peer failure). */
  approvalSlot?:
    | { state: "ready"; props: ApprovalSlotProps }
    | { state: "error"; error: SlotPeerError }
    | { state: "malformed" };
};

export function EvidencePanel({
  caseId,
  caseClient,
  enableApproval = false,
  decisionExpiresAt,
  approvalSlot,
}: Props) {
  const [loading, setLoading] = useState(true);
  const [caseRecord, setCaseRecord] = useState<Case | null>(null);
  const [bundle, setBundle] = useState<EvidenceBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [permission, setPermission] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      setPermission(null);
      try {
        const [c, e] = await Promise.all([
          caseClient.getCase(caseId),
          caseClient.getOpsEvidence(caseId),
        ]);
        if (cancelled) return;
        setCaseRecord(c);
        setBundle(e);
      } catch (err) {
        if (cancelled) return;
        if (
          err instanceof PeerError &&
          (err.httpStatus === 403 || err.code === "FORBIDDEN")
        ) {
          setPermission(`${err.code}: ${err.message}`);
        } else if (err instanceof PeerError) {
          setError(`${err.code}: ${err.message}`);
        } else {
          setError(err instanceof Error ? err.message : "Load failed");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [caseId, caseClient]);

  const defaultApproval = useMemo(() => {
    if (!enableApproval || !caseRecord || !bundle || !decisionExpiresAt) {
      return null;
    }
    const props: ApprovalSlotProps = {
      caseRecord,
      action: {
        ...demoAction,
        status:
          caseRecord.status === "ESCALATED" ? "ESCALATED" : demoAction.status,
      },
      evidence: bundle.evidence,
      decisionExpiresAt,
      decide: (actionId, request) => caseClient.decide(actionId, request),
    };
    return { state: "ready" as const, props };
  }, [enableApproval, caseRecord, bundle, caseClient, decisionExpiresAt]);

  const slot = approvalSlot ?? defaultApproval;

  if (loading) return <UiState tone="loading" title="Loading evidence…" />;
  if (permission) {
    return (
      <UiState
        tone="permission"
        title="Permission denied"
        detail={permission}
      />
    );
  }
  if (error)
    return <UiState tone="error" title="Evidence unavailable" detail={error} />;
  if (!caseRecord || !bundle) {
    return (
      <UiState tone="empty" title="No evidence" detail="Nothing to show." />
    );
  }
  if (bundle.evidence.length === 0) {
    return (
      <UiState
        tone="empty"
        title="Evidence empty"
        detail="No evidence records."
      />
    );
  }

  return (
    <div className="stack">
      <div className="row">
        <h1>Evidence workspace</h1>
        <StatusChip label={labelCaseStatus(caseRecord.status)} />
      </div>
      <p className="muted">
        Pending refund / provider confirmation is not proof of customer credit.
        Escalation is not resolution.
      </p>
      <div className="evidence-grid">
        {bundle.evidence.map((item) => (
          <EvidenceCard key={item.evidence_id} evidence={item} />
        ))}
      </div>
      {slot ? <ApprovalSlot {...slot} /> : null}
    </div>
  );
}

function EvidenceCard({ evidence }: { evidence: Evidence }) {
  const facts = evidence.facts;
  return (
    <article className="panel" data-testid="evidence-card">
      <div className="row">
        <strong>{facts.kind}</strong>
        <span className="muted mono">{evidence.verification_status}</span>
      </div>
      <p className="muted">
        subject{" "}
        <MaskedRef
          label="subject"
          masked={maskSubjectRef(evidence.subject_ref)}
        />
      </p>
      {facts.kind === "PAYMENT" ? (
        <div className="stack" style={{ gap: "0.35rem" }}>
          <MaskedRef
            label="transaction"
            masked={maskTransactionRef(facts.payment.transaction_ref)}
          />
          <MaskedRef
            label="order"
            masked={maskOrderReference(facts.payment.order_reference)}
          />
          <span className="mono">
            {formatAmountMinor(
              facts.payment.amount_minor,
              facts.payment.currency,
            )}
          </span>
        </div>
      ) : null}
      {facts.kind === "ORDER" ? (
        <MaskedRef
          label="order"
          masked={maskOrderReference(facts.order.order_reference)}
        />
      ) : null}
      {facts.kind === "REFUND" ? (
        <div className="stack" style={{ gap: "0.35rem" }}>
          <StatusChip label={labelRefundStatus(facts.refund.status)} />
          <MaskedRef
            label="provider"
            masked={maskProviderRef(facts.refund.provider_ref)}
          />
          <MaskedRef
            label="transaction"
            masked={maskTransactionRef(facts.refund.transaction_ref)}
          />
        </div>
      ) : null}
      {facts.kind === "CREDIT" ? (
        <div className="stack" style={{ gap: "0.35rem" }}>
          <StatusChip label={labelCredit(facts.credit.confirmed)} />
          <MaskedRef
            label="provider"
            masked={maskProviderRef(facts.credit.provider_ref)}
          />
        </div>
      ) : null}
    </article>
  );
}
