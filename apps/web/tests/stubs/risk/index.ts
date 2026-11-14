import type { RiskClient, RiskDashboard } from "@/application/ports";
import { PeerError } from "@/domain/types";

export const FIXTURE_RISK_DASHBOARD: RiskDashboard = {
  open_investigations: 1,
  active_restrictions: 1,
  awaiting_evidence: 0,
  aging_investigations: 1,
  blocked_actions: 1,
};

export type RiskStub = "valid" | "unavailable" | "unauthorized_or_out_of_scope";

export function createRiskStub(scenario: RiskStub = "valid"): RiskClient {
  if (scenario === "unavailable") {
    return {
      async getDashboard() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "risk peer unavailable",
          "req-risk-unavailable",
          503,
        );
      },
    };
  }
  if (scenario === "unauthorized_or_out_of_scope") {
    return {
      async getDashboard() {
        throw new PeerError(
          "FORBIDDEN",
          "Risk dashboard out of scope",
          "req-risk-forbidden",
          403,
        );
      },
    };
  }
  return {
    async getDashboard() {
      return { ...FIXTURE_RISK_DASHBOARD };
    },
  };
}
