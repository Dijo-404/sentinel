import type { OpsTeamClient, OpsTeamMember } from "@/application/ports";
import { PeerError } from "@/domain/types";

/** Seed-aligned fixture ops roster (synthetic; fixture mode only). */
export const FIXTURE_OPS_TEAM: OpsTeamMember[] = [
  {
    user_id: "user-operator-demo",
    email: "operator@example.test",
    display_name: "Demo Operator",
    role: "operator",
  },
  {
    user_id: "user-supervisor-demo",
    email: "supervisor@example.test",
    display_name: "Demo Supervisor",
    role: "supervisor",
  },
];

export type OpsTeamStub = "valid" | "unavailable" | "empty";

export function createOpsTeamStub(
  scenario: OpsTeamStub = "valid",
): OpsTeamClient {
  if (scenario === "unavailable") {
    return {
      async listOpsTeam() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "identity peer unavailable",
          "req-ops-team-unavailable",
          503,
        );
      },
    };
  }
  if (scenario === "empty") {
    return {
      async listOpsTeam() {
        return { members: [], source: "fixture" };
      },
    };
  }
  return {
    async listOpsTeam() {
      return {
        members: FIXTURE_OPS_TEAM.map((m) => ({ ...m })),
        source: "fixture",
      };
    },
  };
}
