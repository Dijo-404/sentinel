import type { ActionState, CaseState } from "./types";

/** Exact operator-facing labels for pending / provider / credit / escalation. */

export type StatusLabelKind =
  | "pending"
  | "provider"
  | "credit"
  | "escalation"
  | "resolved"
  | "in_progress"
  | "needs_input"
  | "other";

export type StatusLabel = {
  kind: StatusLabelKind;
  text: string;
};

const CASE_LABELS: Record<CaseState, StatusLabel> = {
  RECEIVED: { kind: "in_progress", text: "Received" },
  NEEDS_INPUT: { kind: "needs_input", text: "Needs input" },
  INVESTIGATING: { kind: "in_progress", text: "Investigating" },
  RECONCILING: { kind: "in_progress", text: "Reconciling" },
  PLANNING: { kind: "in_progress", text: "Planning" },
  POLICY_CHECK: { kind: "in_progress", text: "Policy check" },
  WAITING_APPROVAL: { kind: "pending", text: "Waiting approval" },
  EXECUTING: { kind: "pending", text: "Executing" },
  VERIFYING: { kind: "pending", text: "Verifying" },
  WAITING_EXTERNAL: { kind: "pending", text: "Pending external" },
  ESCALATED: { kind: "escalation", text: "Escalated" },
  VERIFIED_RESOLVED: { kind: "resolved", text: "Verified resolved" },
  CLOSED_NO_ACTION: { kind: "resolved", text: "Closed — no action" },
};

const ACTION_LABELS: Record<ActionState, StatusLabel> = {
  PROPOSED: { kind: "pending", text: "Proposed" },
  RESERVED: { kind: "pending", text: "Reserved" },
  DISPATCHING: { kind: "pending", text: "Dispatching" },
  OUTCOME_UNKNOWN: { kind: "pending", text: "Outcome unknown" },
  PENDING: { kind: "pending", text: "Pending" },
  PROVIDER_CONFIRMED: { kind: "provider", text: "Provider confirmed" },
  CREDIT_CONFIRMED: { kind: "credit", text: "Credit confirmed" },
  FAILED_FINAL: { kind: "other", text: "Failed final" },
  ESCALATED: { kind: "escalation", text: "Escalated" },
};

export function labelCaseStatus(status: CaseState): StatusLabel {
  return CASE_LABELS[status];
}

export function labelActionStatus(status: ActionState): StatusLabel {
  return ACTION_LABELS[status];
}

/** Refund evidence status → pending / provider labels (credit is separate). */
export function labelRefundStatus(
  status: "PENDING" | "PROVIDER_CONFIRMED" | "FAILED_FINAL",
): StatusLabel {
  switch (status) {
    case "PENDING":
      return { kind: "pending", text: "Pending" };
    case "PROVIDER_CONFIRMED":
      return { kind: "provider", text: "Provider confirmed" };
    case "FAILED_FINAL":
      return { kind: "other", text: "Failed final" };
  }
}

export function labelCredit(confirmed: boolean): StatusLabel {
  return confirmed
    ? { kind: "credit", text: "Credit confirmed" }
    : { kind: "pending", text: "Credit pending" };
}
