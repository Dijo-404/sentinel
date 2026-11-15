"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { CaseClient } from "@/application/ports";
import type { ApprovalSlotProps } from "@/application/ports";
import type { ActionRecord, Approval, Case, Evidence } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { ApprovalSlot } from "@/slots/approval-slot";
import { UiState } from "@/components/ui-states";
import { StatusChip } from "@/components/status-chip";
import { labelActionStatus, labelCaseStatus } from "@/domain/status-labels";
import { formatAmountMinor, maskTransactionRef } from "@/domain/mask";
import { MaskedRef } from "@/components/masked-ref";
import { EvidenceFreshness } from "@/components/ledger/evidence-freshness";

/** Earliest evidence expiry — authoritative freshness bound (both modes). */
export function decisionExpiresFromEvidence(
  evidence: Evidence[],
  approvalExpiresAt?: string,
): string | null {
  if (approvalExpiresAt) return approvalExpiresAt;
  const times = evidence
    .map((e) => e.expires_at)
    .filter((t): t is string => typeof t === "string" && t.length > 0);
  if (times.length === 0) return null;
  return times.reduce((a, b) => (a < b ? a : b));
}

type Props = {
  actionId: string;
  caseClient: CaseClient;
  mode: "fixture" | "real-peers";
  /** Authenticated reviewer for SN-013 ApprovalPanel (real-peers). */
  reviewerId?: string;
  /** Optional clock for ApprovalPanel expiry checks (tests). */
  now?: () => Date;
  /** False for operators: proposal stays visible, decide controls are withheld (server enforces too). */
  canDecide?: boolean;
  /** Override slot for tests (peer failure / malformed). */
  approvalSlot?:
    | { state: "ready"; props: ApprovalSlotProps }
    | { state: "error"; error: PeerError }
    | { state: "malformed" };
};

/**
 * Exact decision workspace: evidence context + approval-ui.v1 slot
 * wired to case-api decide (fixture stub or real-peer proxy).
 * Real-peers loads ActionRecord via getAction (ledger); never demo digests.
 */
export function SupervisorDecisionWorkspace({
  actionId,
  caseClient,
  mode,
  reviewerId,
  now,
  canDecide = true,
  approvalSlot,
}: Props) {
  const [loading, setLoading] = useState(true);
  const [caseRecord, setCaseRecord] = useState<Case | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [action, setAction] = useState<ActionRecord | null>(null);
  const [decisionExpiresAt, setDecisionExpiresAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [permission, setPermission] = useState<string | null>(null);
  const [conflict, setConflict] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [decided, setDecided] = useState<Approval | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  // Sync guard: the slot fires onRefresh right after decide resolves, before re-render.
  const decidedRef = useRef(false);

  // After a decision the case may leave WAITING_APPROVAL, so refetch by id instead of load().
  const refreshAfterDecision = useCallback(
    async (caseId: string) => {
      try {
        const [c, a] = await Promise.all([
          caseClient.getCase(caseId),
          caseClient.getAction(actionId),
        ]);
        setCaseRecord(c);
        setAction(a);
        setRefreshError(null);
      } catch (err) {
        setRefreshError(
          err instanceof PeerError
            ? `${err.code}: ${err.message}`
            : err instanceof Error
              ? err.message
              : "Refresh failed",
        );
      }
    },
    [actionId, caseClient],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPermission(null);
    try {
      const resolvedAction = await caseClient.getAction(actionId);
      const [c, bundle] = await Promise.all([
        caseClient.getCase(resolvedAction.payload.case_id),
        caseClient.getOpsEvidence(resolvedAction.payload.case_id),
      ]);
      // Derive from action/evidence only — never invent a calendar constant.
      const expires = decisionExpiresFromEvidence(
        bundle.evidence,
        resolvedAction.approval?.expires_at,
      );
      if (!expires) {
        throw new PeerError(
          "PROPOSAL_UNAVAILABLE",
          "Decision expiry unavailable — no evidence expires_at or approval window",
          "req-supervisor-expiry-missing",
          503,
        );
      }
      setDecided(resolvedAction.approval ?? null);
      decidedRef.current = Boolean(resolvedAction.approval);
      setCaseRecord(c);
      setEvidence(bundle.evidence);
      setAction(resolvedAction);
      setDecisionExpiresAt(expires);
    } catch (err) {
      if (err instanceof PeerError && (err.httpStatus === 403 || err.code === "FORBIDDEN")) {
        setPermission(`${err.code}: ${err.message}`);
      } else if (err instanceof PeerError) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : "Load failed");
      }
      setCaseRecord(null);
      setEvidence([]);
      setAction(null);
      setDecisionExpiresAt(null);
    } finally {
      setLoading(false);
    }
  }, [actionId, caseClient, mode]);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  if (loading) {
    return <UiState tone="loading" title="Loading decision workspace…" />;
  }
  if (permission) {
    return <UiState tone="permission" title="Permission denied" detail={permission} />;
  }
  if (error) {
    return <UiState tone="error" title="Decision unavailable" detail={error} />;
  }
  if (!caseRecord || !action || !decisionExpiresAt) {
    return <UiState tone="empty" title="No proposal" detail="Nothing to decide." />;
  }

  const slot =
    approvalSlot ??
    ({
      state: "ready" as const,
      props: {
        caseRecord,
        action,
        evidence,
        decisionExpiresAt,
        decide: async (id, request) => {
          // Failures propagate to the slot, which shows the error and re-enables its buttons.
          const approval = await caseClient.decide(id, request);
          decidedRef.current = true;
          setDecided(approval);
          void refreshAfterDecision(caseRecord.case_id);
          return approval;
        },
        onRefresh: () => {
          if (!decidedRef.current) setReloadKey((k) => k + 1);
        },
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
          Exact amount and identifiers from the proposal. No free-text financial edits.
        </p>
        {mode === "fixture" ? (
          <p className="fixture-banner" role="status">
            Fixture mode — local approval-ui substitute + case-api decide stub
          </p>
        ) : (
          <p className="fixture-banner" role="status">
            Real-peer — ledger <code className="mono">GET /v1/actions/…</code> + case-api{" "}
            <code className="mono">POST /v1/ops/actions/…/decisions</code>
          </p>
        )}
        <div className="row">
          <span className="mono decision-amount" data-testid="decision-amount">
            {formatAmountMinor(action.payload.amount_minor, action.payload.currency)}
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
      <EvidenceFreshness evidence={evidence} now={now?.()} />
      {decided ? (
        <section className="panel stack" role="status" data-testid="decision-success">
          <h2>Decision recorded: {decided.decision}</h2>
          <p>
            Approval <code className="mono">{decided.approval_id}</code> by {decided.reviewer_id}.
            {decided.decision === "APPROVE"
              ? "Execution and verification continue server-side; status below is as last returned by case-api and the ledger."
              : "This rejection does not authorize execution. Status below is as last returned by case-api and the ledger."}
          </p>
          <div className="row">
            <StatusChip label={labelCaseStatus(caseRecord.status)} />
            <StatusChip label={labelActionStatus(action.status)} />
          </div>
          {refreshError ? (
            <p role="alert" data-testid="decision-refresh-error">
              Refresh failed — {refreshError}
            </p>
          ) : null}
        </section>
      ) : canDecide ? (
        <ApprovalSlot {...slot} mode={mode} reviewerId={reviewerId} now={now} />
      ) : (
        <UiState
          tone="permission"
          title="Supervisor decision required"
          detail="You can review this proposal. Only a supervisor can approve or reject it."
        />
      )}
    </div>
  );
}
