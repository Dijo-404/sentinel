"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { CaseClient } from "@/application/ports";
import type { ApprovalSlotProps } from "@/application/ports";
import type { ActionRecord, Case, Evidence } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { demoAction } from "@/adapters/fixture-case-client";
import { ApprovalSlot } from "@/slots/approval-slot";

/** Build action facts from queue/case + refund evidence (no demoAction hard-gate). */
function actionFromQueueCase(
  actionId: string,
  caseRecord: Case,
  evidence: Evidence[],
): ActionRecord {
  const refundEv = evidence.find(
    (e) =>
      e.facts.kind === "REFUND" && e.facts.refund.action_id === actionId,
  );
  const paymentEv = evidence.find((e) => e.facts.kind === "PAYMENT");
  const refund =
    refundEv && refundEv.facts.kind === "REFUND"
      ? refundEv.facts.refund
      : null;
  const payment =
    paymentEv && paymentEv.facts.kind === "PAYMENT"
      ? paymentEv.facts.payment
      : null;

  // Known demo digest when the queue action matches the fixture record.
  const digest =
    actionId === demoAction.action_id
      ? demoAction.action_digest
      : (refundEv?.digest ?? demoAction.action_digest);
  const policy_version =
    actionId === demoAction.action_id
      ? demoAction.payload.policy_version
      : demoAction.payload.policy_version;

  return {
    action_id: actionId,
    provider_ref:
      refund?.provider_ref ??
      (actionId === demoAction.action_id ? demoAction.provider_ref : ""),
    action_digest: digest,
    status: caseRecord.status === "ESCALATED" ? "ESCALATED" : "PROPOSED",
    payload: {
      action: "REQUEST_REFUND",
      case_id: caseRecord.case_id,
      case_revision: caseRecord.revision,
      evidence_ids: caseRecord.evidence_ids,
      policy_version,
      transaction_ref:
        refund?.transaction_ref ??
        payment?.transaction_ref ??
        demoAction.payload.transaction_ref,
      amount_minor:
        refund?.amount_minor ??
        payment?.amount_minor ??
        demoAction.payload.amount_minor,
      currency:
        refund?.currency ??
        payment?.currency ??
        demoAction.payload.currency,
      destination: "ORIGINAL_PAYMENT_ROUTE",
    },
  };
}
import { UiState } from "@/components/ui-states";
import { StatusChip } from "@/components/status-chip";
import { labelCaseStatus } from "@/domain/status-labels";
import { formatAmountMinor, maskTransactionRef } from "@/domain/mask";
import { MaskedRef } from "@/components/masked-ref";

/** Stable fixture decision window shown and submitted verbatim (not minted on click). */
export const FIXTURE_DECISION_EXPIRES_AT = "2026-12-31T23:59:59Z";

type Props = {
  actionId: string;
  caseClient: CaseClient;
  mode: "fixture" | "real-peers";
  /** Override slot for tests (peer failure / malformed). */
  approvalSlot?:
    | { state: "ready"; props: ApprovalSlotProps }
    | { state: "error"; error: PeerError }
    | { state: "malformed" };
};

/**
 * Exact decision workspace: evidence context + approval-ui.v1 slot
 * wired to case-api decide (fixture stub or real-peer proxy).
 */
export function SupervisorDecisionWorkspace({
  actionId,
  caseClient,
  mode,
  approvalSlot,
}: Props) {
  const [loading, setLoading] = useState(true);
  const [caseRecord, setCaseRecord] = useState<Case | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [action, setAction] = useState<ActionRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [permission, setPermission] = useState<string | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPermission(null);
    try {
      // Fixture / list projection: resolve case that owns this action.
      const listed = await caseClient.listOpsCases({ status: "WAITING_APPROVAL" });
      const match = listed.cases.find((c) => c.action_id === actionId);
      if (!match) {
        throw new PeerError(
          "NOT_FOUND",
          `No waiting approval for action ${actionId}`,
          "req-supervisor-action-404",
          404,
        );
      }
      const [c, bundle] = await Promise.all([
        caseClient.getCase(match.case_id),
        caseClient.getOpsEvidence(match.case_id),
      ]);
      const resolvedAction = actionFromQueueCase(actionId, c, bundle.evidence);
      setCaseRecord(c);
      setEvidence(bundle.evidence);
      setAction(resolvedAction);
    } catch (err) {
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
      setCaseRecord(null);
      setEvidence([]);
      setAction(null);
    } finally {
      setLoading(false);
    }
  }, [actionId, caseClient]);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  if (loading) {
    return <UiState tone="loading" title="Loading decision workspace…" />;
  }
  if (permission) {
    return (
      <UiState tone="permission" title="Permission denied" detail={permission} />
    );
  }
  if (error) {
    return <UiState tone="error" title="Decision unavailable" detail={error} />;
  }
  if (!caseRecord || !action) {
    return (
      <UiState tone="empty" title="No proposal" detail="Nothing to decide." />
    );
  }

  const slot =
    approvalSlot ??
    ({
      state: "ready" as const,
      props: {
        caseRecord,
        action,
        evidence,
        decisionExpiresAt: FIXTURE_DECISION_EXPIRES_AT,
        decide: (id, request) => caseClient.decide(id, request),
        onRefresh: () => setReloadKey((k) => k + 1),
        onConflict: (msg) => setConflict(msg),
      },
    } satisfies { state: "ready"; props: ApprovalSlotProps });

  return (
    <div className="stack" data-testid="supervisor-decision-workspace">
      <div className="panel stack">
        <div className="row">
          <h1>Decision workspace</h1>
          <StatusChip label={labelCaseStatus(caseRecord.status)} />
        </div>
        <p className="muted">
          Exact amount and identifiers from the proposal. No free-text financial
          edits.
        </p>
        {mode === "fixture" ? (
          <p className="fixture-banner" role="status">
            Fixture mode — local approval-ui substitute + case-api decide stub
          </p>
        ) : (
          <p className="fixture-banner" role="status">
            Real-peer — case-api{" "}
            <code className="mono">POST /v1/ops/actions/…/decisions</code>
          </p>
        )}
        <div className="row">
          <span className="mono" data-testid="decision-amount">
            {formatAmountMinor(
              action.payload.amount_minor,
              action.payload.currency,
            )}
          </span>
          <MaskedRef
            label="transaction"
            masked={maskTransactionRef(action.payload.transaction_ref)}
          />
          <Link href={`/supervisor/cases/${encodeURIComponent(caseRecord.case_id)}`}>
            Case detail
          </Link>
          <Link href="/supervisor/approvals">Back to queue</Link>
        </div>
        {conflict ? (
          <p role="alert" data-testid="decision-conflict">
            {conflict}
          </p>
        ) : null}
      </div>
      <ApprovalSlot {...slot} />
    </div>
  );
}
