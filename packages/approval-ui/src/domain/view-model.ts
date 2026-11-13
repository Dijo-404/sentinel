import type {
  ApprovalUiInput,
  ApprovalViewModel,
  DecisionRequest,
  Decision,
  Evidence,
  EvidenceAge,
  RefundAction,
} from "./types.js";

export class ViewModelError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ViewModelError";
  }
}

function assertPositiveInt(value: number, label: string): void {
  if (!Number.isInteger(value) || value < 1) {
    throw new ViewModelError(`${label} must be a positive integer`);
  }
}

function parseInstant(value: string, label: string): number {
  const ms = Date.parse(value);
  if (Number.isNaN(ms)) {
    throw new ViewModelError(`${label} must be RFC 3339 UTC`);
  }
  return ms;
}

function assertRefundAction(payload: RefundAction): void {
  if (payload.action !== "REQUEST_REFUND") {
    throw new ViewModelError("approval UI only renders REQUEST_REFUND proposals");
  }
  assertPositiveInt(payload.case_revision, "case_revision");
  assertPositiveInt(payload.amount_minor, "amount_minor");
  if (payload.currency !== "INR") {
    throw new ViewModelError("currency must be INR");
  }
  if (payload.destination !== "ORIGINAL_PAYMENT_ROUTE") {
    throw new ViewModelError("destination must be ORIGINAL_PAYMENT_ROUTE");
  }
  if (!payload.transaction_ref) {
    throw new ViewModelError("transaction_ref is required");
  }
  if (!payload.policy_version) {
    throw new ViewModelError("policy_version is required");
  }
  if (!Array.isArray(payload.evidence_ids) || payload.evidence_ids.length < 1) {
    throw new ViewModelError("evidence_ids must be a nonempty list");
  }
}

export function evidenceAges(evidence: Evidence[], now: Date): EvidenceAge[] {
  const nowMs = now.getTime();
  return evidence.map((item) => {
    const observedMs = parseInstant(item.observed_at, "observed_at");
    const expiresMs = parseInstant(item.expires_at, "expires_at");
    return {
      evidence_id: item.evidence_id,
      observed_at: item.observed_at,
      expires_at: item.expires_at,
      age_seconds: Math.max(0, Math.floor((nowMs - observedMs) / 1000)),
      expired: nowMs >= expiresMs,
    };
  });
}

export function buildApprovalViewModel(
  input: ApprovalUiInput,
  reviewerId: string,
  decisionExpiresAt: string,
  now: Date,
): ApprovalViewModel {
  if (!reviewerId) {
    throw new ViewModelError("reviewer identity must come from authenticated session");
  }
  parseInstant(decisionExpiresAt, "decision expires_at");
  assertRefundAction(input.action.payload);

  if (input.case.case_id !== input.action.payload.case_id) {
    throw new ViewModelError("case_id mismatch between case and action");
  }
  if (input.action.action_digest.length !== 64) {
    throw new ViewModelError("action_digest must be sha-256 hex");
  }

  return {
    case_id: input.case.case_id,
    case_revision: input.action.payload.case_revision,
    case_status: input.case.status,
    action_id: input.action.action_id,
    transaction_ref: input.action.payload.transaction_ref,
    amount_minor: input.action.payload.amount_minor,
    currency: input.action.payload.currency,
    policy_version: input.action.payload.policy_version,
    action_digest: input.action.action_digest,
    decision_expires_at: decisionExpiresAt,
    reviewer_id: reviewerId,
    evidence_ages: evidenceAges(input.evidence, now),
  };
}

/** Decision body uses digest/revision/policy from the supplied action, never free-form edits. */
export function buildDecisionRequest(
  actionDigest: string,
  caseRevision: number,
  policyVersion: string,
  expiresAt: string,
  decision: Decision,
): DecisionRequest {
  assertPositiveInt(caseRevision, "case_revision");
  parseInstant(expiresAt, "expires_at");
  return {
    decision,
    action_digest: actionDigest,
    case_revision: caseRevision,
    policy_version: policyVersion,
    expires_at: expiresAt,
  };
}

export function hasExpiredEvidence(ages: EvidenceAge[]): boolean {
  return ages.some((age) => age.expired);
}

export function decisionWindowExpired(expiresAt: string, now: Date): boolean {
  return now.getTime() >= parseInstant(expiresAt, "expires_at");
}
