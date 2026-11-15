import type { MerchantSettings, MerchantStaff, MerchantTeamsClient } from "@/application/ports";
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

/** Seed-aligned fixture settings (synthetic; fixture mode only). */
export const FIXTURE_MERCHANT_SETTINGS: MerchantSettings = {
  tenant_id: "tenant-demo",
  merchant_ref: "merchant-demo-1",
  notification_language: "en",
  notify_disputes: true,
  notify_settlements: true,
};

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
      async getSettings() {
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
      async getSettings() {
        throw new PeerError(
          "NOT_FOUND",
          "Merchant settings not found",
          "req-mt-settings-missing",
          404,
        );
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
    async getSettings() {
      return { ...FIXTURE_MERCHANT_SETTINGS };
    },
  };
}
