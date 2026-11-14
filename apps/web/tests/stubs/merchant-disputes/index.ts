import type {
  DisputeCaseSummary,
  MerchantDisputesClient,
} from "@/application/ports";
import { PeerError } from "@/domain/types";

export const FIXTURE_DISPUTES: DisputeCaseSummary[] = [
  {
    dispute_id: "dispute-seed-demo-1",
    tenant_id: "tenant-demo",
    merchant_ref: "merchant-demo",
    case_id: "case-demo-42",
    reason_code: "FRAUD",
    deadline_at: "2026-11-22T00:00:00Z",
    status: "OPEN",
  },
];

export type DisputesStub = "valid" | "unavailable" | "empty";

export function createMerchantDisputesStub(
  scenario: DisputesStub = "valid",
): MerchantDisputesClient {
  if (scenario === "unavailable") {
    return {
      async listDisputes() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "merchant-disputes peer unavailable",
          "req-md-unavailable",
          503,
        );
      },
    };
  }
  if (scenario === "empty") {
    return {
      async listDisputes() {
        return { disputes: [] };
      },
    };
  }
  return {
    async listDisputes(merchantRef) {
      return {
        disputes: FIXTURE_DISPUTES.map((d) => ({
          ...d,
          merchant_ref: merchantRef || d.merchant_ref,
        })),
      };
    },
  };
}
