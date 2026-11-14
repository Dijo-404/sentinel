import type {
  MerchantStaff,
  MerchantTeamsClient,
} from "@/application/ports";
import { PeerError } from "@/domain/types";

/** Seed-aligned fixture staff (synthetic; fixture mode only). */
export const FIXTURE_MERCHANT_STAFF: MerchantStaff[] = [
  {
    staff_id: "staff-demo-1",
    tenant_id: "tenant-demo",
    merchant_ref: "merchant-demo-1",
    display_name: "Ada Merchant",
    roles: ["operator", "approver"],
    active: true,
    approval_limit_minor: 50000,
    currency: "INR",
  },
];

export type MerchantTeamsStub = "valid" | "unavailable" | "empty";

export function createMerchantTeamsStub(
  scenario: MerchantTeamsStub = "valid",
): MerchantTeamsClient {
  if (scenario === "unavailable") {
    return {
      async listTeam() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "merchant-teams peer unavailable",
          "req-mt-unavailable",
          503,
        );
      },
    };
  }
  if (scenario === "empty") {
    return {
      async listTeam() {
        return { staff: [], source: "local_projection" };
      },
    };
  }
  return {
    async listTeam() {
      return {
        staff: FIXTURE_MERCHANT_STAFF.map((s) => ({
          ...s,
          roles: [...s.roles],
        })),
        source: "local_projection",
      };
    },
  };
}
