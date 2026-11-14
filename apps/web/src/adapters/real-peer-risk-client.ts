import type { RiskClient, RiskDashboard } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type RiskPeerOptions = Omit<PeerJsonOptions, "peerLabel"> & {
  peerLabel?: string;
};

function validateDashboard(json: unknown, requestId: string): RiskDashboard {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Risk dashboard is not an object",
      requestId,
    );
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

export function createRealPeerRiskClient(
  options: RiskPeerOptions,
): RiskClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "risk",
  });

  return {
    getDashboard() {
      return request("GET", "/v1/risk/dashboard", validateDashboard);
    },
  };
}

export function createBffRiskClient(options?: {
  fetchImpl?: typeof fetch;
}): RiskClient {
  return createRealPeerRiskClient({
    baseUrl: "/api/bff/risk",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
