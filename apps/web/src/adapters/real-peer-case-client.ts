import type { CaseClient } from "@/application/ports";
import {
  PeerError,
  isApiError,
  type ActionRecord,
  type Approval,
  type Case,
  type CaseCreate,
  type CaseCreated,
  type CaseEvent,
  type DecisionRequest,
  type EvidenceBundle,
  type OpsCaseList,
} from "@/domain/types";
import {
  validateActionRecord,
  validateCase,
  validateCaseCreated,
  validateEvidenceBundle,
  validateOpsList,
} from "./validate";

export type RealPeerOptions = {
  baseUrl: string;
  /**
   * action-ledger.v1 base (direct URL or same-origin `/api/bff/ledger`).
   * Required for getAction in real-peers.
   */
  ledgerBaseUrl?: string;
  /** Direct peer bearer (server session or service token). */
  bearerToken?: string;
  /**
   * `bearer` — Authorization header (default).
   * `credentials` — same-origin BFF; cookie carries the session (no shared token).
   */
  authMode?: "bearer" | "credentials";
  credentials?: RequestCredentials;
  fetchImpl?: typeof fetch;
};

/**
 * Real-peer case-api.v1 adapter.
 * Never falls back to fixtures on failure — errors stay visible.
 */
export function createRealPeerCaseClient(options: RealPeerOptions): CaseClient {
  const base = options.baseUrl.replace(/\/$/, "");
  const ledgerBase = (options.ledgerBaseUrl ?? "").replace(/\/$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const authMode = options.authMode ?? "bearer";

  if (!base) {
    throw new PeerError(
      "PEER_UNAVAILABLE",
      "CASE_API_BASE_URL is required in real-peers mode",
      "cfg-missing-base",
      503,
    );
  }
  if (authMode === "bearer" && !options.bearerToken) {
    throw new PeerError(
      "UNAUTHORIZED",
      "Session bearer or CASE_API_BEARER_TOKEN required for direct case-api calls",
      "cfg-missing-token",
      401,
    );
  }

  async function requestAt<T>(
    root: string,
    peerLabel: string,
    method: string,
    path: string,
    init?: {
      body?: unknown;
      headers?: Record<string, string>;
      validate: (json: unknown, requestId: string) => T;
    },
  ): Promise<T> {
    const requestId = `web-${crypto.randomUUID()}`;
    let response: Response;
    try {
      response = await fetchImpl(`${root}${path}`, {
        method,
        headers: {
          ...(authMode === "bearer"
            ? { Authorization: `Bearer ${options.bearerToken}` }
            : {}),
          Accept: "application/json",
          "X-Request-Id": requestId,
          ...(init?.body ? { "Content-Type": "application/json" } : {}),
          ...init?.headers,
        },
        credentials: options.credentials,
        body: init?.body ? JSON.stringify(init.body) : undefined,
      });
    } catch (err) {
      throw new PeerError(
        "PEER_UNAVAILABLE",
        err instanceof Error
          ? err.message
          : `Network failure contacting ${peerLabel}`,
        requestId,
        503,
      );
    }

    let json: unknown = undefined;
    const text = await response.text();
    if (text) {
      try {
        json = JSON.parse(text);
      } catch {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Peer returned non-JSON body",
          requestId,
          response.status,
        );
      }
    }

    if (!response.ok) {
      if (isApiError(json)) {
        throw new PeerError(
          json.code,
          json.message,
          json.request_id,
          response.status,
        );
      }
      throw new PeerError(
        response.status === 403 || response.status === 401
          ? "FORBIDDEN"
          : response.status === 503
            ? "PEER_UNAVAILABLE"
            : "PEER_ERROR",
        `${peerLabel} returned HTTP ${response.status}`,
        requestId,
        response.status,
      );
    }

    return init!.validate(json, requestId);
  }

  async function request<T>(
    method: string,
    path: string,
    init?: {
      body?: unknown;
      headers?: Record<string, string>;
      validate: (json: unknown, requestId: string) => T;
    },
  ): Promise<T> {
    return requestAt(base, "Case API", method, path, init);
  }

  return {
    createCase(
      input: CaseCreate,
      idempotencyKey: string,
    ): Promise<CaseCreated> {
      return request("POST", "/v1/cases", {
        body: input,
        headers: { "Idempotency-Key": idempotencyKey },
        validate: validateCaseCreated,
      });
    },
    getCase(caseId: string): Promise<Case> {
      return request("GET", `/v1/cases/${encodeURIComponent(caseId)}`, {
        validate: validateCase,
      });
    },
    postMessage(caseId, body): Promise<Case> {
      return request(
        "POST",
        `/v1/cases/${encodeURIComponent(caseId)}/messages`,
        {
          body,
          validate: validateCase,
        },
      );
    },
    listEvents(caseId, after): Promise<{ events: CaseEvent[] }> {
      const q = after != null ? `?format=json&after=${after}` : "?format=json";
      return request(
        "GET",
        `/v1/cases/${encodeURIComponent(caseId)}/events${q}`,
        {
          validate: (json, requestId) => {
            if (
              !json ||
              typeof json !== "object" ||
              !Array.isArray((json as { events?: unknown }).events)
            ) {
              throw new PeerError(
                "MALFORMED_PEER_RESPONSE",
                "Missing events array",
                requestId,
              );
            }
            return json as { events: CaseEvent[] };
          },
        },
      );
    },
    listOpsCases(query): Promise<OpsCaseList> {
      const params = new URLSearchParams();
      if (query?.status) params.set("status", query.status);
      if (query?.after) params.set("after", query.after);
      const qs = params.toString();
      return request("GET", `/v1/ops/cases${qs ? `?${qs}` : ""}`, {
        validate: validateOpsList,
      });
    },
    getOpsEvidence(caseId: string): Promise<EvidenceBundle> {
      return request(
        "GET",
        `/v1/ops/cases/${encodeURIComponent(caseId)}/evidence`,
        { validate: validateEvidenceBundle },
      );
    },
    getAction(actionId: string): Promise<ActionRecord> {
      if (!ledgerBase) {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "ACTION_LEDGER_BASE_URL (or ledger BFF) required to fetch proposal",
          "cfg-missing-ledger",
          503,
        );
      }
      return requestAt(
        ledgerBase,
        "Action ledger",
        "GET",
        `/v1/actions/${encodeURIComponent(actionId)}`,
        { validate: validateActionRecord },
      );
    },
    decide(actionId: string, decision: DecisionRequest): Promise<Approval> {
      return request(
        "POST",
        `/v1/ops/actions/${encodeURIComponent(actionId)}/decisions`,
        {
          body: decision,
          validate: (json, requestId) => {
            if (!json || typeof json !== "object") {
              throw new PeerError(
                "MALFORMED_PEER_RESPONSE",
                "Approval is not an object",
                requestId,
              );
            }
            return json as Approval;
          },
        },
      );
    },
    escalate(caseId, body): Promise<Case> {
      return request(
        "POST",
        `/v1/ops/cases/${encodeURIComponent(caseId)}/escalate`,
        { body, validate: validateCase },
      );
    },
    getOperatorDashboard() {
      return request("GET", "/v1/operator/dashboard", {
        validate: (json, requestId) => {
          if (!json || typeof json !== "object") {
            throw new PeerError(
              "MALFORMED_PEER_RESPONSE",
              "Operator dashboard is not an object",
              requestId,
            );
          }
          return json as {
            assigned_to_me: number;
            unassigned: number;
            escalated: number;
            waiting_approval: number;
            open_total: number;
          };
        },
      });
    },
    getSupervisorDashboard() {
      return request("GET", "/v1/supervisor/dashboard", {
        validate: (json, requestId) => {
          if (!json || typeof json !== "object") {
            throw new PeerError(
              "MALFORMED_PEER_RESPONSE",
              "Supervisor dashboard is not an object",
              requestId,
            );
          }
          return json as {
            waiting_approval_cases: number;
            escalated_cases: number;
            pending_approvals: number;
            label: string;
          };
        },
      });
    },
    getCustomerDashboard() {
      return request("GET", "/v1/customer/dashboard", {
        validate: (json, requestId) => {
          if (!json || typeof json !== "object") {
            throw new PeerError(
              "MALFORMED_PEER_RESPONSE",
              "Customer dashboard is not an object",
              requestId,
            );
          }
          return json as {
            open_cases: number;
            needs_input: number;
            waiting_approval: number;
            verified_resolved: number;
          };
        },
      });
    },
    listCustomerCases() {
      return request("GET", "/v1/customer/cases", {
        validate: (json, requestId) => {
          if (
            !json ||
            typeof json !== "object" ||
            !Array.isArray((json as { cases?: unknown }).cases)
          ) {
            throw new PeerError(
              "MALFORMED_PEER_RESPONSE",
              "Missing cases array",
              requestId,
            );
          }
          const cases = (json as { cases: unknown[] }).cases.map((row, i) => {
            if (!row || typeof row !== "object") {
              throw new PeerError(
                "MALFORMED_PEER_RESPONSE",
                `Customer case[${i}] is not an object`,
                requestId,
              );
            }
            const o = row as Record<string, unknown>;
            if (
              typeof o.case_id !== "string" ||
              typeof o.status !== "string" ||
              typeof o.revision !== "number" ||
              !Number.isInteger(o.revision) ||
              typeof o.language !== "string"
            ) {
              throw new PeerError(
                "MALFORMED_PEER_RESPONSE",
                `Customer case[${i}] missing required fields`,
                requestId,
              );
            }
            return {
              case_id: o.case_id,
              status: o.status as Case["status"],
              revision: o.revision,
              language: o.language,
            };
          });
          return { cases };
        },
      });
    },
  };
}
