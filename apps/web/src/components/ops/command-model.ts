import type { OpsAuditEvent } from "@/application/ports";
import type { Case, CaseState } from "@/domain/types";

/** Linear progress of a case through the money path; escalation and no-action close sit off it. */
const STAGE: Record<CaseState, number> = {
  RECEIVED: 0,
  NEEDS_INPUT: 0,
  INVESTIGATING: 1,
  RECONCILING: 1,
  PLANNING: 2,
  POLICY_CHECK: 2,
  WAITING_APPROVAL: 2,
  EXECUTING: 3,
  WAITING_EXTERNAL: 3,
  VERIFYING: 4,
  VERIFIED_RESOLVED: 5,
  ESCALATED: -1,
  CLOSED_NO_ACTION: -2,
};

export const STAGE_NAMES = ["Intake", "Investigate", "Approve", "Dispatch", "Verify", "Verified"] as const;

export type CommandModel = {
  total: number;
  /** Cases at or past each linear stage (funnel). */
  reached: number[];
  /** Cases currently sitting at each linear stage. */
  at: number[];
  escalated: number;
  closedNoAction: number;
  waitingApproval: number;
  inFlight: number;
  verified: number;
};

/** Pure projection of real case rows into command-center numbers. Deduplicates by case_id. */
export function buildCommandModel(cases: Case[]): CommandModel {
  const byId = new Map<string, Case>();
  for (const c of cases) {
    const prev = byId.get(c.case_id);
    if (!prev || c.revision >= prev.revision) byId.set(c.case_id, c);
  }
  const rows = [...byId.values()];
  const at = Array(STAGE_NAMES.length).fill(0) as number[];
  let escalated = 0;
  let closedNoAction = 0;
  for (const c of rows) {
    const s = STAGE[c.status];
    if (s === -1) escalated++;
    else if (s === -2) closedNoAction++;
    else at[s]++;
  }
  const reached = at.map((_, i) => at.slice(i).reduce((a, b) => a + b, 0));
  return {
    total: rows.length,
    reached,
    at,
    escalated,
    closedNoAction,
    waitingApproval: rows.filter((c) => c.status === "WAITING_APPROVAL").length,
    inFlight: at[3] + at[4],
    verified: at[5],
  };
}

/** Audit events per hour for the last `hours`, oldest first, relative to `now`. */
export function hourlyBuckets(events: OpsAuditEvent[], now: Date, hours = 24): number[] {
  const out = Array(hours).fill(0) as number[];
  const end = now.getTime();
  for (const e of events) {
    const t = Date.parse(e.occurred_at);
    if (Number.isNaN(t)) continue;
    const ago = Math.floor((end - t) / 3_600_000);
    if (ago >= 0 && ago < hours) out[hours - 1 - ago]++;
  }
  return out;
}
