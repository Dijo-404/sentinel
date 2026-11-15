import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { OpsCombinedOverview } from "@/components/dashboards/ops-combined-overview";
import { createCaseApiStub } from "../stubs/case-api";
import type { AuthSession } from "@/lib/server/auth";
import { opsPortalNav, PORTAL_NAV } from "@/lib/portal-nav";

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

describe("ops shared nav", () => {
  it("operator and supervisor share the same menu set", () => {
    const op = opsPortalNav("operator").map((i) => i.label);
    const su = opsPortalNav("supervisor").map((i) => i.label);
    expect(op).toEqual(su);
    expect(op).toEqual([
      "Dashboard",
      "Command center",
      "Queue",
      "Approvals",
      "Escalations",
      "Messages",
      "Assistant",
      "Knowledge",
      "Activity",
      "History",
      "Team",
      "Audit",
    ]);
    expect(PORTAL_NAV.operator.map((i) => i.label)).toEqual(op);
    expect(PORTAL_NAV.supervisor.map((i) => i.label)).toEqual(su);
    expect(opsPortalNav("operator")[0]?.href).toBe("/operator/dashboard");
    expect(opsPortalNav("supervisor")[0]?.href).toBe("/supervisor/dashboard");
  });
});

describe("OpsCombinedOverview", () => {
  it("renders operator and supervisor KPIs together", async () => {
    const client = createCaseApiStub("valid");
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <OpsCombinedOverview session={sessionStub} caseClient={client} mode="fixture" />
      </ShellProvider>,
    );
    expect(screen.getByTestId("ops-combined-dashboard")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("operator-kpi-row")).toBeInTheDocument();
      expect(screen.getByTestId("supervisor-kpi-row")).toBeInTheDocument();
    });
  });

  it("keeps supervisor section when operator projection is missing", async () => {
    const client = createCaseApiStub("valid");
    delete client.getOperatorDashboard;
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <OpsCombinedOverview session={sessionStub} caseClient={client} mode="fixture" />
      </ShellProvider>,
    );
    await waitFor(() => {
      expect(screen.getByTestId("supervisor-kpi-row")).toBeInTheDocument();
    });
    expect(screen.getByText("Operator metrics unavailable")).toBeInTheDocument();
  });
});
