/** Wire types for web-shell.v1 consuming case-api.v1 / approval-ui.v1 / voice.v1. */

export const CONTRACT_VERSION = "sentinel.task-contracts.v1" as const;
export const CONTRACT_SHA256 =
  "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb" as const;

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

export type Principal = {
  principal_id: string;
  tenant_id: string;
  roles: string[];
  subject_refs: string[];
  case_ids: string[];
};

export type ApiError = {
  code: string;
  message: string;
  request_id: string;
};

export type Capabilities = {
  contract_version: Version;
  component: string;
  mode: "fixture" | "real-peers";
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

export type CaseCreate = {
  message: string;
  language: string;
  order_reference: string;
  channel: "web" | "voice";
};

export type CaseCreated = {
  case_id: string;
  status: "RECEIVED";
  status_url: string;
};

export type CaseEvent = {
  event_id: string;
  sequence: number;
  case_id: string;
  case_revision: number;
  type: string;
  occurred_at: string;
  payload: {
    status: CaseState;
    evidence_ids: string[];
    action_id?: string;
    reason_code: string;
  };
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

export type Evidence = {
  evidence_id: string;
  case_id: string;
  source: string;
  subject_ref: string;
  observed_at: string;
  expires_at: string;
  digest: string;
  verification_status: "VERIFIED" | "UNVERIFIED" | "CONFLICTING";
  facts:
    | { kind: "PAYMENT"; payment: Payment }
    | { kind: "ORDER"; order: Order }
    | { kind: "REFUND"; refund: Refund }
    | { kind: "CREDIT"; credit: Credit };
};

export type EvidenceBundle = {
  contract_version: Version;
  case_id: string;
  evidence: Evidence[];
  reconciliation_codes: string[];
};

export type RefundAction = {
  action: "REQUEST_REFUND";
  case_id: string;
  case_revision: number;
  evidence_ids: string[];
  policy_version: string;
  transaction_ref: string;
  amount_minor: number;
  currency: "INR";
  destination: "ORIGINAL_PAYMENT_ROUTE";
};

export type Approval = {
  approval_id: string;
  action_digest: string;
  case_revision: number;
  policy_version: string;
  decision: "APPROVE" | "REJECT";
  reviewer_id: string;
  expires_at: string;
};

export type DecisionRequest = {
  decision: "APPROVE" | "REJECT";
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

export type VoiceRequest = {
  language: string;
  audio_uri?: string;
  text?: string;
  consent: boolean;
};

export type VoiceResult = {
  original_text: string;
  language: string;
  ambiguous: boolean;
  reason_codes: string[];
  /** recorded = fixture/Sarvam fixtures; live = live-provider. Never invent. */
  evidence_mode?: string;
};

export type OpsCaseList = {
  cases: Case[];
  next_cursor?: string;
};

export class PeerError extends Error {
  readonly code: string;
  readonly requestId: string;
  readonly httpStatus?: number;

  constructor(
    code: string,
    message: string,
    requestId: string,
    httpStatus?: number,
  ) {
    super(message);
    this.name = "PeerError";
    this.code = code;
    this.requestId = requestId;
    this.httpStatus = httpStatus;
  }
}

export function isApiError(value: unknown): value is ApiError {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.code === "string" &&
    typeof v.message === "string" &&
    typeof v.request_id === "string"
  );
}
