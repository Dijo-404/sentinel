import type { CaseClient } from "@/application/ports";
import {
  CONTRACT_VERSION,
  PeerError,
  type ActionRecord,
  type Approval,
  type Case,
  type CaseCreate,
  type CaseCreated,
  type CaseEvent,
  type CaseState,
  type DecisionRequest,
  type EvidenceBundle,
  type OpsCaseList,
} from "@/domain/types";

import caseDemo from "../../../contracts/fixtures/case-demo.json";
import evidenceBundle from "../../../contracts/fixtures/evidence-bundle.json";
import actionRecord from "../../../contracts/fixtures/action-record.json";

export type StubCase =
  | "valid"
  | "unavailable"
  | "malformed"
  | "unauthorized_or_out_of_scope";

export type CaseApiStubOptions = {
  /** Role used for decide authorization. Default: deny unless `"supervisor"`. */
  reviewerRole?: string;
};

const demoCase = caseDemo as Case;
const demoEvidence = evidenceBundle as EvidenceBundle;
export const demoAction = actionRecord as ActionRecord;

const DEMO_CASE_EVENTS: CaseEvent[] = [
  {
    event_id: "evt-1",
    sequence: 1,
    case_id: "case-demo-42",
    case_revision: 1,
    type: "CASE_CREATED",
    occurred_at: "2026-11-13T11:59:00Z",
    payload: {
      status: "RECEIVED",
      evidence_ids: [],
      reason_code: "INTAKE",
    },
  },
  {
    event_id: "evt-2",
    sequence: 2,
    case_id: "case-demo-42",
    case_revision: 2,
    type: "STATUS_CHANGED",
    occurred_at: "2026-11-13T12:00:30Z",
    payload: {
      status: "WAITING_APPROVAL",
      evidence_ids: ["evidence-payment-b", "evidence-order"],
      action_id: "action-demo-1",
      reason_code: "SUPERVISOR_REQUIRED",
    },
  },
];

function fail(
  code: string,
  message: string,
  requestId: string,
  httpStatus?: number,
): never {
  throw new PeerError(code, message, requestId, httpStatus);
}

/** Local case-api.v1 double. Never silently succeeds when configured to fail. */
export function createCaseApiStub(
  scenario: StubCase = "valid",
  options?: CaseApiStubOptions,
): CaseClient {
  if (scenario === "unavailable") {
    return unavailableClient();
  }
  if (scenario === "malformed") {
    return malformedClient();
  }
  if (scenario === "unauthorized_or_out_of_scope") {
    return unauthorizedClient();
  }
  return validClient(options);
}

function validClient(options?: CaseApiStubOptions): CaseClient {
  const reviewerRole = options?.reviewerRole;
  const cases = new Map<string, Case>([
    [demoCase.case_id, { ...demoCase }],
  ]);
  const eventsByCase = new Map<string, CaseEvent[]>([
    [demoCase.case_id, DEMO_CASE_EVENTS.map((e) => ({ ...e, payload: { ...e.payload } }))],
  ]);
  let nextCaseNum = 1;
  let nextEventSeq = 100;

  function allocateCaseId(): string {
    while (cases.has(`case-demo-${nextCaseNum}`)) {
      nextCaseNum += 1;
    }
    const id = `case-demo-${nextCaseNum}`;
    nextCaseNum += 1;
    return id;
  }

  function requireCase(caseId: string): Case {
    const current = cases.get(caseId);
    if (!current) {
      fail("NOT_FOUND", "Case not found", "req-get-404", 404);
    }
    return current;
  }

  function appendEvent(
    caseId: string,
    type: string,
    status: CaseState,
    reason_code: string,
    revision: number,
  ): void {
    const list = eventsByCase.get(caseId) ?? [];
    const sequence =
      list.length === 0
        ? 1
        : Math.max(...list.map((e) => e.sequence)) + 1;
    nextEventSeq += 1;
    list.push({
      event_id: `evt-${nextEventSeq}`,
      sequence,
      case_id: caseId,
      case_revision: revision,
      type,
      occurred_at: new Date().toISOString(),
      payload: {
        status,
        evidence_ids: [...(cases.get(caseId)?.evidence_ids ?? [])],
        action_id: cases.get(caseId)?.action_id,
        reason_code,
      },
    });
    eventsByCase.set(caseId, list);
  }

  return {
    async createCase(
      input: CaseCreate,
      _idempotencyKey: string,
    ): Promise<CaseCreated> {
      if (!input.message?.trim() || !input.order_reference?.trim()) {
        fail(
          "INVALID_INPUT",
          "message and order_reference required",
          "req-create-422",
          422,
        );
      }
      const caseId = allocateCaseId();
      const created: Case = {
        contract_version: CONTRACT_VERSION,
        case_id: caseId,
        revision: 1,
        status: "RECEIVED",
        language: input.language || "en-IN",
        intent: "UNKNOWN",
        evidence_ids: [],
      };
      cases.set(caseId, created);
      eventsByCase.set(caseId, []);
      appendEvent(caseId, "CASE_CREATED", "RECEIVED", "INTAKE", 1);
      return {
        case_id: caseId,
        status: "RECEIVED",
        status_url: `/cases/${caseId}`,
      };
    },
    async getCase(caseId: string): Promise<Case> {
      return { ...requireCase(caseId) };
    },
    async postMessage(caseId, body) {
      const current = requireCase(caseId);
      if (body.expected_revision !== current.revision) {
        fail("REVISION_CONFLICT", "Stale case revision", "req-msg-409", 409);
      }
      const updated: Case = {
        ...current,
        revision: current.revision + 1,
        status: "NEEDS_INPUT",
      };
      cases.set(caseId, updated);
      appendEvent(
        caseId,
        "MESSAGE_ADDED",
        updated.status,
        "OPERATOR_MESSAGE",
        updated.revision,
      );
      return { ...updated };
    },
    async listEvents(caseId, after = 0) {
      requireCase(caseId);
      const list = eventsByCase.get(caseId) ?? [];
      return { events: list.filter((e) => e.sequence > after) };
    },
    async listOpsCases(query): Promise<OpsCaseList> {
      if (query?.after) {
        return { cases: [], next_cursor: undefined };
      }
      return {
        cases: [...cases.values()].map((c) => ({ ...c })),
        next_cursor: undefined,
      };
    },
    async getOpsEvidence(caseId: string): Promise<EvidenceBundle> {
      requireCase(caseId);
      return structuredClone(demoEvidence);
    },
    async getAction(actionId: string): Promise<ActionRecord> {
      if (actionId !== demoAction.action_id) {
        fail("NOT_FOUND", "Action not found", "req-action-404", 404);
      }
      return structuredClone(demoAction);
    },
    async decide(
      actionId: string,
      request: DecisionRequest,
    ): Promise<Approval> {
      if (reviewerRole !== "supervisor") {
        fail(
          "FORBIDDEN",
          "Supervisor role required to decide",
          "req-decide-403",
          403,
        );
      }
      if (actionId !== demoAction.action_id) {
        fail("NOT_FOUND", "Action not found", "req-decide-404", 404);
      }
      if (request.action_digest !== demoAction.action_digest) {
        fail(
          "DIGEST_MISMATCH",
          "Action digest mismatch",
          "req-decide-409",
          409,
        );
      }
      return {
        approval_id: "approval-demo-1",
        action_digest: request.action_digest,
        case_revision: request.case_revision,
        policy_version: request.policy_version,
        decision: request.decision,
        reviewer_id: "supervisor-demo-1",
        expires_at: request.expires_at,
      };
    },
    async escalate(caseId, body) {
      const current = requireCase(caseId);
      if (body.expected_revision !== current.revision) {
        fail("REVISION_CONFLICT", "Stale case revision", "req-esc-409", 409);
      }
      const updated: Case = {
        ...current,
        revision: current.revision + 1,
        status: "ESCALATED",
        contract_version: CONTRACT_VERSION,
      };
      cases.set(caseId, updated);
      appendEvent(
        caseId,
        "ESCALATED",
        updated.status,
        "OPERATOR_ESCALATION",
        updated.revision,
      );
      return { ...updated };
    },
    async getOperatorDashboard() {
      return {
        assigned_to_me: 1,
        unassigned: 0,
        escalated: 0,
        waiting_approval: 1,
        open_total: 1,
      };
    },
    async getSupervisorDashboard() {
      return {
        waiting_approval_cases: 1,
        escalated_cases: 0,
        pending_approvals: 1,
        label: "fixture-projection",
      };
    },
    async getCustomerDashboard() {
      return {
        open_cases: 1,
        needs_input: 0,
        waiting_approval: 1,
        verified_resolved: 0,
      };
    },
  };
}

function unavailableClient(): CaseClient {
  const boom = async () =>
    fail(
      "PEER_UNAVAILABLE",
      "Required peer unavailable",
      "req-unavailable",
      503,
    );
  return {
    createCase: boom,
    getCase: boom,
    postMessage: boom,
    listEvents: boom,
    listOpsCases: boom,
    getOpsEvidence: boom,
    getAction: boom,
    decide: boom,
    escalate: boom,
    getOperatorDashboard: boom,
    getSupervisorDashboard: boom,
    getCustomerDashboard: boom,
  };
}

function malformedClient(): CaseClient {
  return {
    async createCase() {
      return { case_id: "", status: "RECEIVED", status_url: "" } as CaseCreated;
    },
    async getCase() {
      return { case_id: "x" } as unknown as Case;
    },
    async postMessage() {
      return { bad: true } as unknown as Case;
    },
    async listEvents() {
      return { events: [{ sequence: "nope" }] as unknown as CaseEvent[] };
    },
    async listOpsCases() {
      return { cases: "nope" } as unknown as OpsCaseList;
    },
    async getOpsEvidence() {
      return { evidence: null } as unknown as EvidenceBundle;
    },
    async getAction() {
      return { action_id: "x" } as unknown as ActionRecord;
    },
    async decide() {
      return { decision: "MAYBE" } as unknown as Approval;
    },
    async escalate() {
      return { status: "DONE" } as unknown as Case;
    },
  };
}

function unauthorizedClient(): CaseClient {
  const boom = async () =>
    fail("FORBIDDEN", "Out of scope for principal", "req-forbidden", 403);
  return {
    createCase: boom,
    getCase: boom,
    postMessage: boom,
    listEvents: boom,
    listOpsCases: boom,
    getOpsEvidence: boom,
    getAction: boom,
    decide: boom,
    escalate: boom,
    getOperatorDashboard: boom,
    getSupervisorDashboard: boom,
    getCustomerDashboard: boom,
  };
}

export const STUB_SCENARIOS: StubCase[] = [
  "valid",
  "unavailable",
  "malformed",
  "unauthorized_or_out_of_scope",
];
