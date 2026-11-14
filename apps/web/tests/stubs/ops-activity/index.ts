import type { ActivityItem, OpsActivityClient } from "@/application/ports";
import { PeerError } from "@/domain/types";

/** Seed-aligned fixture activity (synthetic; fixture mode only). */
export const FIXTURE_ACTIVITY: ActivityItem[] = [
  {
    activity_id: "act-seed-case-demo-42",
    kind: "case.opened",
    summary: "Sandbox case case-demo-42 opened",
    occurred_at: "2026-11-14T10:00:00Z",
    case_id: "case-demo-42",
  },
];

export type OpsActivityStub = "valid" | "unavailable" | "empty";

export function createOpsActivityStub(
  scenario: OpsActivityStub = "valid",
): OpsActivityClient {
  if (scenario === "unavailable") {
    return {
      async listActivity() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "ops-activity peer unavailable",
          "req-oa-unavailable",
          503,
        );
      },
    };
  }
  if (scenario === "empty") {
    return {
      async listActivity() {
        return { items: [], source: "fixture" };
      },
    };
  }
  return {
    async listActivity() {
      return {
        items: FIXTURE_ACTIVITY.map((row) => ({ ...row })),
        source: "fixture",
      };
    },
  };
}
