import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { PortalDashboard } from "@/components/dashboards/portal-dashboard";
import type { AuthSession } from "@/lib/server/auth";
import { createRiskStub } from "../stubs/risk";

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
    email: "risk@example.test",
    display_name: "Demo Risk",
    password: "x",
    account_status: "ACTIVE" as const,
    account_class: "staff" as const,
    assignments: [],
  },
  assignment: {
    assignment_id: "a1",
    role: "risk" as const,
    tenant_id: "t1",
    label: "Fraud desk",
  },
  workspaces: [],
} satisfies AuthSession;

describe("risk portal dashboard", () => {
  it("fixture shows risk.v1 dashboard KPIs", async () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <PortalDashboard role="risk" session={sessionStub} riskClient={createRiskStub("valid")} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("risk-kpi-row")).toBeInTheDocument();
    expect(screen.getByText("Open investigations")).toBeInTheDocument();
    expect(screen.getByText("Active restrictions")).toBeInTheDocument();
  });

  it("real-peers failure shows unavailable — no fake counts", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <PortalDashboard
          role="risk"
          session={sessionStub}
          riskClient={createRiskStub("unavailable")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-empty")).toHaveTextContent("Metrics unavailable");
    expect(screen.queryByTestId("risk-kpi-row")).not.toBeInTheDocument();
  });
});
