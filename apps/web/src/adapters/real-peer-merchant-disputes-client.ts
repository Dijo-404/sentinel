import type {
  DisputeCaseSummary,
  MerchantDisputesClient,
} from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type MerchantDisputesPeerOptions = Omit<
  PeerJsonOptions,
  "peerLabel"
> & {
  peerLabel?: string;
};

function validateList(
  json: unknown,
  requestId: string,
): { disputes: DisputeCaseSummary[] } {
  if (
    !json ||
    typeof json !== "object" ||
    !Array.isArray((json as { disputes?: unknown }).disputes)
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Missing disputes array",
      requestId,
    );
  }
  const disputes = (json as { disputes: unknown[] }).disputes.map((row, i) => {
    if (!row || typeof row !== "object") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Dispute[${i}] is not an object`,
        requestId,
      );
    }
    const o = row as Record<string, unknown>;
    if (
      typeof o.dispute_id !== "string" ||
      typeof o.merchant_ref !== "string" ||
      typeof o.case_id !== "string" ||
      typeof o.status !== "string" ||
      typeof o.reason_code !== "string" ||
      typeof o.deadline_at !== "string" ||
      typeof o.tenant_id !== "string"
    ) {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Dispute[${i}] missing required fields`,
        requestId,
      );
    }
    return {
      dispute_id: o.dispute_id,
      tenant_id: o.tenant_id,
      merchant_ref: o.merchant_ref,
      case_id: o.case_id,
      reason_code: o.reason_code,
      deadline_at: o.deadline_at,
      status: o.status,
    } satisfies DisputeCaseSummary;
  });
  return { disputes };
}

export function createRealPeerMerchantDisputesClient(
  options: MerchantDisputesPeerOptions,
): MerchantDisputesClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "merchant-disputes",
  });

  return {
    listDisputes(merchantRef) {
      return request(
        "GET",
        `/v1/merchants/${encodeURIComponent(merchantRef)}/disputes`,
        validateList,
      );
    },
  };
}

/** Browser path: same-origin BFF with session cookie. */
export function createBffMerchantDisputesClient(options?: {
  fetchImpl?: typeof fetch;
}): MerchantDisputesClient {
  return createRealPeerMerchantDisputesClient({
    baseUrl: "/api/bff/merchant-disputes",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
