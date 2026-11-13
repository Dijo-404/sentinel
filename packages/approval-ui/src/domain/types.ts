/** Wire types from sentinel.task-contracts.v1 (subset consumed by approval-ui.v1). */

export const CONTRACT_VERSION = "sentinel.task-contracts.v1" as const;
export type Version = typeof CONTRACT_VERSION;

export type CaseState =
  | "RECEIVED"
  | "NEEDS_INPUT"
  | "INVESTIGATING"
  | "RECONCILING"
  | "PLANNING"
  | "POLICY_CHECK"
  | "WAITING_APPROVAL"
  | "EXECUTING"
  | "VERIFYING"
  | "WAITING_EXTERNAL"
  | "ESCALATED"
  | "VERIFIED_RESOLVED"
  | "CLOSED_NO_ACTION";

export type ActionState =
  | "PROPOSED"
  | "RESERVED"
  | "DISPATCHING"
  | "OUTCOME_UNKNOWN"
  | "PENDING"
  | "PROVIDER_CONFIRMED"
  | "CREDIT_CONFIRMED"
  | "FAILED_FINAL"
  | "ESCALATED";

export type VerificationStatus = "VERIFIED" | "UNVERIFIED" | "CONFLICTING";

export type Decision = "APPROVE" | "REJECT";

export type WireError = {
  code: string;
  message: string;
  request_id: string;
};

export type Principal = {
  principal_id: string;
  tenant_id: string;
  roles: string[];
  subject_refs: string[];
  case_ids: string[];
};

export type Case = {
  contract_version: Version;
  case_id: string;
  revision: number;
  status: CaseState;
  language: string;
  intent: string;
  evidence_ids: string[];
  action_id?: string;
};

export type Payment = {
  transaction_ref: string;
  order_reference: string;
  subject_ref: string;
  status: "CAPTURED" | "PENDING" | "FAILED";
  amount_minor: number;
  currency: "INR";
};

export type Order = {
  order_reference: string;
  subject_ref: string;
  fulfilled_order_count: number;
  merchant_confirmed_duplicate: boolean;
  paid: boolean;
};

export type Refund = {
  action_id: string;
  provider_ref: string;
  transaction_ref: string;
  amount_minor: number;
  currency: "INR";
  status: "PENDING" | "PROVIDER_CONFIRMED" | "FAILED_FINAL";
};

export type Credit = {
  provider_ref: string;
  confirmed: boolean;
  observed_at: string;
};

export type EvidenceFacts =
  | { kind: "PAYMENT"; payment: Payment }
  | { kind: "ORDER"; order: Order }
  | { kind: "REFUND"; refund: Refund }
  | { kind: "CREDIT"; credit: Credit };

export type Evidence = {
  evidence_id: string;
  case_id: string;
  source: string;
  subject_ref: string;
  observed_at: string;
  expires_at: string;
  digest: string;
  verification_status: VerificationStatus;
  facts: EvidenceFacts;
};

export type RefundAction = {
  action: "REQUEST_REFUND";
  case_id: string;
  case_revision: number;
  transaction_ref: string;
  amount_minor: number;
  currency: "INR";
  destination: "ORIGINAL_PAYMENT_ROUTE";
  evidence_ids: string[];
  policy_version: string;
};

export type Approval = {
  approval_id: string;
  action_digest: string;
  case_revision: number;
  policy_version: string;
  decision: Decision;
  reviewer_id: string;
  expires_at: string;
};

export type DecisionRequest = {
  decision: Decision;
  action_digest: string;
  case_revision: number;
  policy_version: string;
  expires_at: string;
};

export type ActionRecord = {
  action_id: string;
  provider_ref: string;
  payload: RefundAction;
  action_digest: string;
  status: ActionState;
  approval?: Approval;
};

/** Host input for the embeddable approval surface (approval-ui.v1). */
export type ApprovalUiInput = {
  case: Case;
  action: ActionRecord;
  evidence: Evidence[];
};

export type EvidenceAge = {
  evidence_id: string;
  observed_at: string;
  expires_at: string;
  age_seconds: number;
  expired: boolean;
};

export type ApprovalViewModel = {
  case_id: string;
  case_revision: number;
  case_status: CaseState;
  action_id: string;
  transaction_ref: string;
  amount_minor: number;
  currency: "INR";
  policy_version: string;
  action_digest: string;
  decision_expires_at: string;
  reviewer_id: string;
  evidence_ages: EvidenceAge[];
};

export type RefreshEvent = {
  kind: "refresh";
  reason_code: string;
  request_id?: string;
};

export type ConflictEvent = {
  kind: "conflict";
  reason_code: string;
  request_id?: string;
  status: number;
};

export type DecisionOutcome =
  | { ok: true; approval: Approval }
  | { ok: false; status: number; error: WireError; ui_code: DecisionUiCode };

export type DecisionUiCode =
  | "EXPIRED"
  | "STALE"
  | "UNAUTHORIZED"
  | "CROSS_TENANT"
  | "CONFLICT"
  | "UNAVAILABLE"
  | "MALFORMED"
  | "UNKNOWN";
