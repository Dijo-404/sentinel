import type {
  MerchantAnalyticsClient,
  MerchantMetrics,
} from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type MerchantAnalyticsPeerOptions = Omit<
  PeerJsonOptions,
  "peerLabel"
> & {
  peerLabel?: string;
};

function validateMetrics(json: unknown, requestId: string): MerchantMetrics {
  if (!json || typeof json !== "object") {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Merchant metrics is not an object",
      requestId,
    );
  }
  const o = json as Record<string, unknown>;
  if (
    typeof o.merchant_ref !== "string" ||
    typeof o.unresolved_minor !== "number" ||
    !Number.isInteger(o.unresolved_minor) ||
    typeof o.currency !== "string" ||
    typeof o.exception_rate !== "string"
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Merchant metrics missing required fields",
      requestId,
    );
  }
  return o as MerchantMetrics;
}

export function createRealPeerMerchantAnalyticsClient(
  options: MerchantAnalyticsPeerOptions,
): MerchantAnalyticsClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "merchant-analytics",
  });

  return {
    getMetrics(merchantRef, window) {
      const params = new URLSearchParams({
        window_start: window.window_start,
        window_end: window.window_end,
      });
      return request(
        "GET",
        `/v1/merchants/${encodeURIComponent(merchantRef)}/metrics?${params}`,
        validateMetrics,
      );
    },
  };
}

/** Browser path: same-origin BFF with session cookie. */
export function createBffMerchantAnalyticsClient(options?: {
  fetchImpl?: typeof fetch;
}): MerchantAnalyticsClient {
  return createRealPeerMerchantAnalyticsClient({
    baseUrl: "/api/bff/merchant-analytics",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
