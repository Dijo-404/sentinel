import type { MerchantAnalyticsClient, MerchantMetrics } from "@/application/ports";
import { PeerError } from "@/domain/types";

/** Expected-metrics shape from merchant-analytics contracts (fixture mode). */
export const FIXTURE_MERCHANT_METRICS: MerchantMetrics = {
  tenant_id: "tenant-demo",
  merchant_ref: "merchant-demo-1",
  window_start: "2026-11-01T00:00:00Z",
  window_end: "2026-11-14T00:00:00Z",
  exception_rate: "0.4000",
  unresolved_minor: 100000,
  currency: "INR",
  refund_aging_buckets: {
    "0-24h": 1,
    "1-3d": 1,
    "3-7d": 1,
    "7d+": 0,
  },
  median_handling_seconds: 2700,
  top_causes: [
    "DUPLICATE_PAYMENT",
    "PAID_UNFULFILLED",
    "UNMATCHED_PAYMENT",
    "STATUS_UPDATE",
  ],
};

export type MerchantAnalyticsStub =
  | "valid"
  | "unavailable"
  | "unauthorized_or_out_of_scope";

export function createMerchantAnalyticsStub(
  scenario: MerchantAnalyticsStub = "valid",
): MerchantAnalyticsClient {
  if (scenario === "unavailable") {
    return {
      async getMetrics() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "merchant-analytics peer unavailable",
          "req-ma-unavailable",
          503,
        );
      },
    };
  }
  if (scenario === "unauthorized_or_out_of_scope") {
    return {
      async getMetrics() {
        throw new PeerError(
          "FORBIDDEN",
          "Merchant metrics out of scope",
          "req-ma-forbidden",
          403,
        );
      },
    };
  }
  return {
    async getMetrics(merchantRef, window) {
      return {
        ...FIXTURE_MERCHANT_METRICS,
        merchant_ref: merchantRef || FIXTURE_MERCHANT_METRICS.merchant_ref,
        window_start: window.window_start,
        window_end: window.window_end,
      };
    },
  };
}
