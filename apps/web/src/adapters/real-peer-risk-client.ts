import type {
  RiskClient,
  RiskDashboard,
  RiskFinding,
  RiskInvestigation,
  RiskReport,
  RiskRestriction,
} from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type RiskPeerOptions = Omit<PeerJsonOptions, "peerLabel"> & {
  peerLabel?: string;
};

function validateDashboard(json: unknown, requestId: string): RiskDashboard {
  if (!json || typeof json !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Risk dashboard is not an object", requestId);
  }
  const o = json as Record<string, unknown>;
  for (const key of [
    "open_investigations",
    "active_restrictions",
    "awaiting_evidence",
    "aging_investigations",
    "blocked_actions",
  ] as const) {
    if (typeof o[key] !== "number" || !Number.isInteger(o[key])) {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Risk dashboard missing integer ${key}`,
        requestId,
      );
    }
  }
  return {
    open_investigations: o.open_investigations as number,
    active_restrictions: o.active_restrictions as number,
    awaiting_evidence: o.awaiting_evidence as number,
    aging_investigations: o.aging_investigations as number,
    blocked_actions: o.blocked_actions as number,
  };
}

function validateReport(json: unknown, requestId: string): RiskReport {
  const dash = validateDashboard(json, requestId);
  const o = json as Record<string, unknown>;
  if (typeof o.report_kind !== "string" || !o.report_kind.trim()) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Risk report missing report_kind", requestId);
  }
  return { ...dash, report_kind: o.report_kind };
}

function requireString(
  o: Record<string, unknown>,
  key: string,
  requestId: string,
  label: string,
): string {
  const v = o[key];
  if (typeof v !== "string" || !v.trim()) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", `${label} missing string ${key}`, requestId);
  }
  return v;
}

function validateInvestigations(
  json: unknown,
  requestId: string,
): { investigations: RiskInvestigation[] } {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Risk investigations response is not an object",
      requestId,
    );
  }
  const raw = (json as Record<string, unknown>).investigations;
  if (!Array.isArray(raw)) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Risk investigations missing array", requestId);
  }
  const investigations = raw.map((item, i) => {
    if (!item || typeof item !== "object") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Risk investigation[${i}] is not an object`,
        requestId,
      );
    }
    const o = item as Record<string, unknown>;
    return {
      investigation_id: requireString(o, "investigation_id", requestId, "investigation"),
      case_id: requireString(o, "case_id", requestId, "investigation"),
      status: requireString(o, "status", requestId, "investigation"),
      reason_code: requireString(o, "reason_code", requestId, "investigation"),
      queue_ref: requireString(o, "queue_ref", requestId, "investigation"),
      severity: requireString(o, "severity", requestId, "investigation"),
      updated_at: requireString(o, "updated_at", requestId, "investigation"),
    };
  });
  return { investigations };
}

function validateRestrictions(
  json: unknown,
  requestId: string,
): { restrictions: RiskRestriction[] } {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Risk restrictions response is not an object",
      requestId,
    );
  }
  const raw = (json as Record<string, unknown>).restrictions;
  if (!Array.isArray(raw)) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Risk restrictions missing array", requestId);
  }
  const restrictions = raw.map((item, i) => {
    if (!item || typeof item !== "object") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Risk restriction[${i}] is not an object`,
        requestId,
      );
    }
    const o = item as Record<string, unknown>;
    const txn = o.transaction_ref;
    if (txn !== null && txn !== undefined && typeof txn !== "string") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Risk restriction[${i}] bad transaction_ref`,
        requestId,
      );
    }
    if (typeof o.blocks_financial_actions !== "boolean") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Risk restriction[${i}] missing blocks_financial_actions`,
        requestId,
      );
    }
    if (typeof o.financial_approval_granted !== "boolean") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Risk restriction[${i}] missing financial_approval_granted`,
        requestId,
      );
    }
    return {
      restriction_id: requireString(o, "restriction_id", requestId, "restriction"),
      case_id: requireString(o, "case_id", requestId, "restriction"),
      investigation_id: requireString(o, "investigation_id", requestId, "restriction"),
      status: requireString(o, "status", requestId, "restriction"),
      reason_code: requireString(o, "reason_code", requestId, "restriction"),
      blocks_financial_actions: o.blocks_financial_actions,
      transaction_ref: typeof txn === "string" ? txn : null,
      financial_approval_granted: o.financial_approval_granted,
    };
  });
  return { restrictions };
}

function validateFindings(json: unknown, requestId: string): { findings: RiskFinding[] } {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Risk findings response is not an object",
      requestId,
    );
  }
  const raw = (json as Record<string, unknown>).findings;
  if (!Array.isArray(raw)) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Risk findings missing array", requestId);
  }
  const findings = raw.map((item, i) => {
    if (!item || typeof item !== "object") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Risk finding[${i}] is not an object`,
        requestId,
      );
    }
    const o = item as Record<string, unknown>;
    return {
      finding_id: requireString(o, "finding_id", requestId, "finding"),
      investigation_id: requireString(o, "investigation_id", requestId, "finding"),
      classification: requireString(o, "classification", requestId, "finding"),
      notes: typeof o.notes === "string" ? o.notes : "",
      recorded_at: requireString(o, "recorded_at", requestId, "finding"),
    };
  });
  return { findings };
}

function queryString(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) q.set(k, v);
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

export function createRealPeerRiskClient(options: RiskPeerOptions): RiskClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "risk",
  });

  return {
    getDashboard() {
      return request("GET", "/v1/risk/dashboard", validateDashboard);
    },
    listInvestigations() {
      return request("GET", "/v1/risk/investigations", validateInvestigations);
    },
    listRestrictions(query) {
      const path =
        "/v1/risk/restrictions" +
        queryString({
          blocks_financial_actions:
            query?.blocks_financial_actions === undefined
              ? undefined
              : String(query.blocks_financial_actions),
          has_transaction_ref:
            query?.has_transaction_ref === undefined
              ? undefined
              : String(query.has_transaction_ref),
        });
      return request("GET", path, validateRestrictions);
    },
    listFindings() {
      return request("GET", "/v1/risk/findings", validateFindings);
    },
    getReports() {
      return request("GET", "/v1/risk/reports", validateReport);
    },
  };
}

export function createBffRiskClient(options?: { fetchImpl?: typeof fetch }): RiskClient {
  return createRealPeerRiskClient({
    baseUrl: "/api/bff/risk",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
