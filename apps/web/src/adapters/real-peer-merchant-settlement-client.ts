import type { MerchantSettlementClient, SettlementFinding } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type SettlementPeerOptions = Omit<PeerJsonOptions, "peerLabel"> & {
  peerLabel?: string;
};

function validateFindings(json: unknown, requestId: string): { findings: SettlementFinding[] } {
  if (
    !json ||
    typeof json !== "object" ||
    !Array.isArray((json as { findings?: unknown }).findings)
  ) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Missing findings array", requestId);
  }
  const findings = (json as { findings: unknown[] }).findings.map((row, i) => {
    if (!row || typeof row !== "object") {
      throw new PeerError("MALFORMED_PEER_RESPONSE", `Finding[${i}] is not an object`, requestId);
    }
    const o = row as Record<string, unknown>;
    if (typeof o.finding_id !== "string" || typeof o.status !== "string") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Finding[${i}] missing finding_id/status`,
        requestId,
      );
    }
    const out: SettlementFinding = {
      finding_id: o.finding_id,
      status: o.status,
    };
    if (typeof o.batch_id === "string") out.batch_id = o.batch_id;
    if (typeof o.kind === "string") out.kind = o.kind;
    if (typeof o.expected_minor === "number" && Number.isInteger(o.expected_minor)) {
      out.expected_minor = o.expected_minor;
    }
    if (typeof o.observed_minor === "number" && Number.isInteger(o.observed_minor)) {
      out.observed_minor = o.observed_minor;
    }
    if (typeof o.currency === "string") out.currency = o.currency;
    return out;
  });
  return { findings };
}

export function createRealPeerMerchantSettlementClient(
  options: SettlementPeerOptions,
): MerchantSettlementClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "merchant-settlement",
  });

  return {
    listFindings(query) {
      const params = new URLSearchParams();
      if (query?.batch_id) params.set("batch_id", query.batch_id);
      if (query?.status) params.set("status", query.status);
      const qs = params.toString();
      return request("GET", `/v1/settlements/findings${qs ? `?${qs}` : ""}`, validateFindings);
    },
  };
}

export function createBffMerchantSettlementClient(options?: {
  fetchImpl?: typeof fetch;
}): MerchantSettlementClient {
  return createRealPeerMerchantSettlementClient({
    baseUrl: "/api/bff/merchant-settlement",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
