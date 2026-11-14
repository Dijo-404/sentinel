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

/** risk.v1 investigation list row (portal queue). */
export type RiskInvestigation = {
  investigation_id: string;
  case_id: string;
  status: string;
  reason_code: string;
  queue_ref: string;
  severity: string;
  updated_at: string;
};

/** risk.v1 restriction list row (portal holds / transactions). */
export type RiskRestriction = {
  restriction_id: string;
  case_id: string;
  investigation_id: string;
  status: string;
  reason_code: string;
  blocks_financial_actions: boolean;
  transaction_ref: string | null;
  financial_approval_granted: boolean;
};

/** risk.v1 finding list row (portal audit). */
export type RiskFinding = {
  finding_id: string;
  investigation_id: string;
  classification: string;
  notes: string;
  recorded_at: string;
};

/** risk.v1 reports read model (dashboard + report_kind). */
export type RiskReport = RiskDashboard & { report_kind: string };

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

/** Ops message inbox row from GET /v1/ops/messages. */
export type OpsMessage = {
  case_id: string;
  message_id: string;
  text: string;
  language: string;
  author: string;
  occurred_at: string;
};

/** Ops audit event row from GET /v1/ops/audit-events. */
export type OpsAuditEvent = {
  case_id: string;
  sequence: number;
  type: string;
  occurred_at: string;
  payload: Record<string, unknown>;
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
  /**
   * Ops case queue — GET /v1/ops/cases.
   * `status` accepts a CaseState, comma-separated states, or alias `HISTORY`
   * (= VERIFIED_RESOLVED | CLOSED_NO_ACTION on case-api).
   */
  listOpsCases(query?: {
    status?: string;
    after?: string;
  }): Promise<OpsCaseList>;
  /** Ops message inbox — GET /v1/ops/messages. */
  listOpsMessages(): Promise<{ messages: OpsMessage[]; next_cursor?: string }>;
  /** Ops audit feed — GET /v1/ops/audit-events. */
  listOpsAuditEvents(): Promise<{
    events: OpsAuditEvent[];
    next_cursor?: string;
  }>;
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

/** Optional risk.v1 client (dashboard + portal list reads). */
export interface RiskClient {
  getDashboard(): Promise<RiskDashboard>;
  listInvestigations(): Promise<{ investigations: RiskInvestigation[] }>;
  listRestrictions(query?: {
    blocks_financial_actions?: boolean;
    has_transaction_ref?: boolean;
  }): Promise<{ restrictions: RiskRestriction[] }>;
  listFindings(): Promise<{ findings: RiskFinding[] }>;
  getReports(): Promise<RiskReport>;
}

/** Optional merchant-settlement.v1 findings client. */
export interface MerchantSettlementClient {
  listFindings(query?: {
    batch_id?: string;
    status?: string;
  }): Promise<{ findings: SettlementFinding[] }>;
}

/** merchant-disputes.v1 DisputeCase list row (display fields). */
export type DisputeCaseSummary = {
  dispute_id: string;
  tenant_id: string;
  merchant_ref: string;
  case_id: string;
  reason_code: string;
  deadline_at: string;
  status: string;
};

/** merchant-inbox.v1 ExceptionItem list row (display fields). */
export type InboxExceptionItem = {
  item_id: string;
  tenant_id: string;
  merchant_ref: string;
  kind: string;
  amount_minor: number;
  currency: string;
  status: string;
  case_id?: string;
  transaction_ref?: string;
  assignee?: string;
};

/** Optional merchant-disputes.v1 client. */
export interface MerchantDisputesClient {
  listDisputes(merchantRef: string): Promise<{ disputes: DisputeCaseSummary[] }>;
}

/** Optional merchant-inbox.v1 exceptions client. */
export interface MerchantInboxClient {
  listExceptions(query?: {
    merchant_ref?: string;
    kind?: string;
    status?: string;
  }): Promise<{ items: InboxExceptionItem[] }>;
}

/** merchant-teams.v1 MerchantStaff wire shape (display fields). */
export type MerchantStaff = {
  staff_id: string;
  tenant_id: string;
  merchant_ref: string;
  display_name: string;
  roles: string[];
  active: boolean;
  approval_limit_minor?: number;
  currency?: string;
};

/** merchant-teams.v1 MerchantSettings wire shape. */
export type MerchantSettings = {
  tenant_id: string;
  merchant_ref: string;
  notification_language: string;
  notify_disputes: boolean;
  notify_settlements: boolean;
};

/** Optional merchant-teams.v1 team + settings client. */
export interface MerchantTeamsClient {
  listTeam(merchantRef: string): Promise<{
    staff: MerchantStaff[];
    source: "identity_projection" | "local_projection" | string;
  }>;
  getSettings(merchantRef: string): Promise<MerchantSettings>;
}

/** identity.v1 ops team member (supervisor-safe roster row). */
export type OpsTeamMember = {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
};

/** Optional identity.v1 ops team client via BFF `/api/bff/identity`. */
export interface OpsTeamClient {
  listOpsTeam(): Promise<{
    members: OpsTeamMember[];
    source: "identity" | "fixture" | string;
  }>;
}

/** ops-activity.v1 feed row. */
export type ActivityItem = {
  activity_id: string;
  kind: string;
  summary: string;
  occurred_at: string;
  case_id?: string;
};

/** Optional ops-activity.v1 client via BFF `/api/bff/ops-activity`. */
export interface OpsActivityClient {
  listActivity(): Promise<{
    items: ActivityItem[];
    source: "live" | "fixture" | string;
  }>;
}

/** knowledge.v1 article summary. */
export type KnowledgeArticleSummary = {
  article_id: string;
  title: string;
  summary: string;
  updated_at: string;
};

/** knowledge.v1 full article. */
export type KnowledgeArticle = KnowledgeArticleSummary & {
  body: string;
};

/** Optional knowledge.v1 client via BFF `/api/bff/knowledge`. */
export interface KnowledgeClient {
  listArticles(): Promise<{
    articles: KnowledgeArticleSummary[];
    source: "live" | "fixture" | string;
  }>;
  getArticle(articleId: string): Promise<KnowledgeArticle>;
  search(q: string): Promise<{
    hits: KnowledgeArticleSummary[];
    source: "live" | "fixture" | string;
  }>;
}

export type AssistantRole = "customer" | "operator";

/** assistant.v1 thread summary. */
export type AssistantThread = {
  thread_id: string;
  title: string;
  updated_at: string;
};

/** assistant.v1 message row. */
export type AssistantMessage = {
  message_id: string;
  role: "user" | "assistant" | "system";
  text: string;
  evidence_mode: string;
  created_at: string;
};

/** Optional assistant.v1 client via BFF `/api/bff/assistant`. */
export interface AssistantClient {
  listThreads(role: AssistantRole): Promise<{
    threads: AssistantThread[];
    source: "live" | "fixture" | string;
  }>;
  listMessages(threadId: string): Promise<{
    messages: AssistantMessage[];
    source: "live" | "fixture" | string;
  }>;
  postMessage(threadId: string, text: string): Promise<AssistantMessage>;
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
