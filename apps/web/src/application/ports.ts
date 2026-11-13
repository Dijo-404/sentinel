import type {
  ActionRecord,
  Approval,
  Case,
  CaseCreate,
  CaseCreated,
  CaseEvent,
  DecisionRequest,
  Evidence,
  EvidenceBundle,
  OpsCaseList,
  Principal,
  VoiceRequest,
  VoiceResult,
} from "@/domain/types";

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
  decide(
    actionId: string,
    request: DecisionRequest,
  ): Promise<Approval>;
  escalate(
    caseId: string,
    body: {
      expected_revision: number;
      reason_code: string;
      owner_queue: string;
    },
  ): Promise<Case>;
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
