import type { MerchantSettlementClient, SettlementFinding } from "@/application/ports";
import { PeerError } from "@/domain/types";

export const FIXTURE_SETTLEMENT_FINDINGS: SettlementFinding[] = [
  {
    finding_id: "finding-demo-1",
    batch_id: "batch-demo-1",
    status: "OPEN",
    kind: "SHORT_SETTLE",
    expected_minor: 150000,
    currency: "INR",
  },
  {
    finding_id: "finding-demo-2",
    batch_id: "batch-demo-1",
    status: "ASSIGNED",
    kind: "FEE_DIFF",
    expected_minor: 42000,
    currency: "INR",
  },
];

export type SettlementStub = "valid" | "unavailable";

export function createMerchantSettlementStub(
  scenario: SettlementStub = "valid",
): MerchantSettlementClient {
  if (scenario === "unavailable") {
    return {
      async listFindings() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "merchant-settlement peer unavailable",
          "req-ms-unavailable",
          503,
        );
      },
    };
  }
  return {
    async listFindings() {
      return { findings: FIXTURE_SETTLEMENT_FINDINGS.map((f) => ({ ...f })) };
    },
  };
}
