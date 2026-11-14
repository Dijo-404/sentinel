import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import {
  OperatorOverview,
  deriveOperatorKpis,
  statusHistogram,
} from "@/components/dashboards/operator-overview";
import { OperatorQueue } from "@/components/operator-queue";
import { createCaseApiStub } from "../stubs/case-api";
import type { AuthSession } from "@/lib/server/auth";
import type { Case } from "@/domain/types";
import { CONTRACT_VERSION } from "@/domain/types";

const sessionStub = {
  session: {
    session_id: "s1",
    user_id: "u1",
    active_assignment_id: "a1",
    issued_at: "2026-01-01T00:00:00Z",
    expires_at: "2026-01-02T00:00:00Z",
    revoked: false,
  },
  user: {
    user_id: "u1",
    email: "operator@example.test",
    display_name: "Demo Operator",
    password: "x",
    account_status: "ACTIVE" as const,
    account_class: "staff" as const,
    assignments: [],
  },
  assignment: {
    assignment_id: "a1",
    role: "operator" as const,
    tenant_id: "t1",
    label: "Support desk",
  },
  workspaces: [],
} satisfies AuthSession;

function caseOf(status: Case["status"], id = "case-1"): Case {
  return {
    contract_version: CONTRACT_VERSION,
    case_id: id,
    revision: 1,
    status,
    language: "en-IN",
    intent: "DUPLICATE_PAYMENT",
    evidence_ids: [],
  };
}

describe("operator dashboard overview", () => {
  it("renders operator-dashboard with KPIs, fixture banner, and status chart", async () => {
    render(
      <OperatorOverview
        session={sessionStub}
        caseClient={createCaseApiStub("valid")}
      />,
    );

    expect(await screen.findByTestId("operator-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("fixture-banner")).toHaveTextContent(
      "Simulator / fixture — not live production metrics",
    );
    expect(screen.getByText("Open")).toBeInTheDocument();
    expect(screen.getByText("Waiting")).toBeInTheDocument();
    expect(screen.getByText("Overdue")).toBeInTheDocument();
    expect(screen.getByText("Interventions")).toBeInTheDocument();
    expect(screen.getByTestId("chart-card")).toBeInTheDocument();
    expect(screen.getByTestId("operator-status-chart")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open full queue/i })).toHaveAttribute(
      "href",
      "/operator/queue",
    );
    expect(screen.queryByTestId("approval-slot")).not.toBeInTheDocument();
  });

  it("derives open/waiting/interventions from cases; overdue stays unset", () => {
    const cases = [
      caseOf("WAITING_APPROVAL", "c1"),
      caseOf("ESCALATED", "c2"),
      caseOf("VERIFIED_RESOLVED", "c3"),
      caseOf("INVESTIGATING", "c4"),
    ];
    const kpis = deriveOperatorKpis(cases);
    expect(kpis.open).toBe(3);
    expect(kpis.waiting).toBe(1);
    expect(kpis.interventions).toBe(1);
    expect(kpis.overdue).toBeNull();

    const hist = statusHistogram(cases);
    expect(hist).toEqual(
      expect.arrayContaining([
        { name: "Waiting approval", value: 1 },
        { name: "Escalated", value: 1 },
        { name: "Verified resolved", value: 1 },
        { name: "Investigating", value: 1 },
      ]),
    );
  });

  it("falls back to fixture KPIs when peer list fails in fixture mode", async () => {
    render(
      <OperatorOverview
        session={sessionStub}
        caseClient={createCaseApiStub("unavailable")}
        mode="fixture"
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("operator-dashboard")).toBeInTheDocument();
      expect(screen.getByTestId("fixture-banner")).toBeInTheDocument();
    });
    expect(screen.getByText("Open")).toBeInTheDocument();
    expect(screen.queryByTestId("approval-slot")).not.toBeInTheDocument();
  });
});

describe("operator queue wire", () => {
  it("renders queue without approval-slot", async () => {
    render(<OperatorQueue caseClient={createCaseApiStub("valid")} />);
    expect(await screen.findByRole("table", { name: "Operator cases" })).toBeInTheDocument();
    expect(screen.queryByTestId("approval-slot")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve|reject/i })).toBeNull();
  });
});
