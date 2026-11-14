import type {
  RiskClient,
  RiskDashboard,
  RiskFinding,
  RiskInvestigation,
  RiskReport,
  RiskRestriction,
} from "@/application/ports";
import { PeerError } from "@/domain/types";

export const FIXTURE_RISK_DASHBOARD: RiskDashboard = {
  open_investigations: 1,
  active_restrictions: 1,
  awaiting_evidence: 0,
  aging_investigations: 1,
  blocked_actions: 1,
};

export const FIXTURE_RISK_INVESTIGATION: RiskInvestigation = {
  investigation_id: "inv-seed-case-demo-42",
  case_id: "case-demo-42",
  status: "OPEN",
  reason_code: "SUSPECTED_DUPLICATE",
  queue_ref: "FRAUD",
  severity: "HIGH",
  updated_at: "2026-11-15T00:00:00Z",
};

export const FIXTURE_RISK_RESTRICTION: RiskRestriction = {
  restriction_id: "rst-seed-case-demo-42",
  case_id: "case-demo-42",
  investigation_id: "inv-seed-case-demo-42",
  status: "ACTIVE",
  reason_code: "SUSPECTED_DUPLICATE",
  blocks_financial_actions: true,
  transaction_ref: "TXN-B",
  financial_approval_granted: false,
};

export const FIXTURE_RISK_FINDING: RiskFinding = {
  finding_id: "fnd-seed-case-demo-42",
  investigation_id: "inv-seed-case-demo-42",
  classification: "SUSPICIOUS",
  notes: "synthetic-sandbox",
  recorded_at: "2026-11-15T00:00:00Z",
};

export const FIXTURE_RISK_REPORT: RiskReport = {
  ...FIXTURE_RISK_DASHBOARD,
  report_kind: "summary",
};

export type RiskStub = "valid" | "unavailable" | "unauthorized_or_out_of_scope";

function unavailableClient(): RiskClient {
  const fail = async () => {
    throw new PeerError(
      "PEER_UNAVAILABLE",
      "risk peer unavailable",
      "req-risk-unavailable",
      503,
    );
  };
  return {
    getDashboard: fail,
    listInvestigations: fail,
    listRestrictions: fail,
    listFindings: fail,
    getReports: fail,
  };
}

function forbiddenClient(): RiskClient {
  const fail = async () => {
    throw new PeerError(
      "FORBIDDEN",
      "Risk dashboard out of scope",
      "req-risk-forbidden",
      403,
    );
  };
  return {
    getDashboard: fail,
    listInvestigations: fail,
    listRestrictions: fail,
    listFindings: fail,
    getReports: fail,
  };
}

export function createRiskStub(scenario: RiskStub = "valid"): RiskClient {
  if (scenario === "unavailable") return unavailableClient();
  if (scenario === "unauthorized_or_out_of_scope") return forbiddenClient();
  return {
    async getDashboard() {
      return { ...FIXTURE_RISK_DASHBOARD };
    },
    async listInvestigations() {
      return { investigations: [{ ...FIXTURE_RISK_INVESTIGATION }] };
    },
    async listRestrictions() {
      return { restrictions: [{ ...FIXTURE_RISK_RESTRICTION }] };
    },
    async listFindings() {
      return { findings: [{ ...FIXTURE_RISK_FINDING }] };
    },
    async getReports() {
      return { ...FIXTURE_RISK_REPORT };
    },
  };
}
