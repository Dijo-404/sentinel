import type {
  ActionRecord,
  Approval,
  Case,
  CaseCreate,
  CaseCreated,
  CaseEvent,
  CaseState,
  DecisionRequest,
  Evidence,
  EvidenceBundle,
  OpsCaseList,
  Principal,
  VoiceRequest,
  VoiceResult,
} from "@/domain/types";

/** Customer-scoped case list row from GET /v1/customer/cases. */
export type CustomerCaseSummary = {
  case_id: string;
  status: CaseState;
  revision: number;
  language: string;
};

export type CustomerCaseList = { cases: CustomerCaseSummary[] };

/** merchant-analytics.v1 MerchantMetrics wire shape. */
export type MerchantMetrics = {
  tenant_id: string;
  merchant_ref: string;
  window_start: string;
  window_end: string;
  exception_rate: string;
  unresolved_minor: number;
  currency: string;
  refund_aging_buckets: Record<string, number>;
  median_handling_seconds: number;
  top_causes: string[];
};

/** risk.v1 DashboardView wire shape (counts only for KPI row). */
export type RiskDashboard = {
  open_investigations: number;
  active_restrictions: number;
  awaiting_evidence: number;
  aging_investigations: number;
  blocked_actions: number;
};

/** merchant-settlement.v1 findings list item (display fields). */
export type SettlementFinding = {
  finding_id: string;
  batch_id?: string;
  status: string;
  kind?: string;
  /** Wire uses expected_minor / observed_minor — not payment authority. */
  expected_minor?: number;
  observed_minor?: number;
  currency?: string;
};

/** Injected case-api.v1 client used by the shell. */
export interface CaseClient {
  createCase(input: CaseCreate, idempotencyKey: string): Promise<CaseCreated>;
  getCase(caseId: string): Promise<Case>;
  postMessage(
    caseId: string,
    body: { message: string; language: string; expected_revision: number },
  ): Promise<Case>;
  listEvents(caseId: string, after?: number): Promise<{ events: CaseEvent[] }>;
  listOpsCases(query?: {
    status?: string;
    after?: string;
  }): Promise<OpsCaseList>;
  getOpsEvidence(caseId: string): Promise<EvidenceBundle>;
  /**
   * Authoritative ledger proposal (amount, digest, revision, policy_version).
   * Real-peers: action-ledger GET /v1/actions/{id} (via ledger BFF when browser).
   * Never reconstruct from demoAction digests.
   */
  getAction(actionId: string): Promise<ActionRecord>;
  decide(actionId: string, request: DecisionRequest): Promise<Approval>;
  escalate(
    caseId: string,
    body: {
      expected_revision: number;
      reason_code: string;
      owner_queue: string;
    },
  ): Promise<Case>;
  /** Customer-scoped list — GET /v1/customer/cases. */
  listCustomerCases?(): Promise<CustomerCaseList>;
  /** Scoped case-api dashboard projection when available. */
  getOperatorDashboard?(): Promise<{
    assigned_to_me: number;
    unassigned: number;
    escalated: number;
    waiting_approval: number;
    open_total: number;
  }>;
  getSupervisorDashboard?(): Promise<{
    waiting_approval_cases: number;
    escalated_cases: number;
    pending_approvals: number;
    label: string;
  }>;
  getCustomerDashboard?(): Promise<{
    open_cases: number;
    needs_input: number;
    waiting_approval: number;
    verified_resolved: number;
  }>;
}

/** Optional merchant-analytics.v1 client. */
export interface MerchantAnalyticsClient {
  getMetrics(
    merchantRef: string,
    window: { window_start: string; window_end: string },
  ): Promise<MerchantMetrics>;
}

/** Optional risk.v1 dashboard client. */
export interface RiskClient {
  getDashboard(): Promise<RiskDashboard>;
}

/** Optional merchant-settlement.v1 findings client. */
export interface MerchantSettlementClient {
  listFindings(query?: {
    batch_id?: string;
    status?: string;
  }): Promise<{ findings: SettlementFinding[] }>;
}

/** Optional voice.v1 port. Disabled by default in composition. */
export interface VoiceClient {
  transcribe(request: VoiceRequest): Promise<VoiceResult>;
}

/** Props the approval-ui.v1 slot must accept (local substitute or real peer). */
export type ApprovalSlotProps = {
  caseRecord: Case;
  action: ActionRecord;
  evidence: Evidence[];
  /** Authoritative decision window; decide() must send this exact value. */
  decisionExpiresAt: string;
  decide: (actionId: string, request: DecisionRequest) => Promise<Approval>;
  onRefresh?: () => void;
  onConflict?: (message: string) => void;
};

export type ShellMode = "fixture" | "real-peers";

export type ShellConfig = {
  mode: ShellMode;
  voiceEnabled: boolean;
  contractVersion: string;
  contractSha256: string;
  caseApiBaseUrl?: string;
  bearerToken?: string;
  principal: Principal;
};
