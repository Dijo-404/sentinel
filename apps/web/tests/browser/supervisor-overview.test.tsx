import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { SupervisorOverview } from "@/components/dashboards/supervisor-overview";
import type { AuthSession } from "@/lib/server/auth";
import { createCaseApiStub } from "../stubs/case-api";

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
    email: "supervisor@example.test",
    display_name: "Demo Supervisor",
    password: "x",
    account_status: "ACTIVE" as const,
    account_class: "staff" as const,
    assignments: [],
  },
  assignment: {
    assignment_id: "a1",
    role: "supervisor" as const,
    tenant_id: "t1",
    label: "Approvals desk",
  },
  workspaces: [],
} satisfies AuthSession;

function realPeersConfig() {
  return loadShellConfig({
    NEXT_PUBLIC_SHELL_MODE: "real-peers",
    CASE_API_BASE_URL: "http://127.0.0.1:9",
  });
}

describe("supervisor overview", () => {
  it("renders KPIs from getSupervisorDashboard projection", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <SupervisorOverview
          session={sessionStub}
          caseClient={createCaseApiStub("valid")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("supervisor-kpi-row")).toBeInTheDocument();
    expect(screen.getByTestId("fixture-banner")).toBeInTheDocument();
    expect(screen.getByTestId("supervisor-projection-label")).toHaveTextContent(
      "fixture-projection",
    );
    expect(screen.getByTestId("supervisor-projection-chart")).toBeInTheDocument();
    expect(screen.getByText("Waiting approval")).toBeInTheDocument();
    expect(screen.getByText("Escalated")).toBeInTheDocument();
    expect(screen.getByText("Pending approvals")).toBeInTheDocument();
    expect(screen.queryByTestId("supervisor-pipeline")).not.toBeInTheDocument();
  });

  it("real-peers peer failure shows error — no silent fixture fill", async () => {
    render(
      <ShellProvider config={realPeersConfig()}>
        <SupervisorOverview
          session={sessionStub}
          caseClient={createCaseApiStub("unavailable")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-error")).toHaveTextContent(
      "Overview unavailable",
    );
    expect(screen.getByTestId("state-error")).toHaveTextContent(
      "PEER_UNAVAILABLE",
    );
    expect(screen.queryByTestId("fixture-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("supervisor-kpi-row")).not.toBeInTheDocument();
  });

  it("real-peers missing case client shows error — never fake KPIs", async () => {
    render(
      <ShellProvider config={realPeersConfig()}>
        <SupervisorOverview session={sessionStub} caseClient={null} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-error")).toHaveTextContent(
      "Overview unavailable",
    );
    expect(screen.getByTestId("state-error")).toHaveTextContent(
      "PEER_UNAVAILABLE",
    );
    expect(screen.queryByTestId("fixture-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("supervisor-kpi-row")).not.toBeInTheDocument();
  });

  it("fixture mode missing case client shows unavailable — never fake KPIs", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <SupervisorOverview session={sessionStub} caseClient={null} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-error")).toHaveTextContent(
      "Overview unavailable",
    );
    expect(screen.queryByTestId("supervisor-kpi-row")).not.toBeInTheDocument();
  });

  it("missing dashboard method shows unavailable — never listOpsCases KPIs", async () => {
    const client = createCaseApiStub("valid");
    delete client.getSupervisorDashboard;
    render(
      <ShellProvider config={realPeersConfig()}>
        <SupervisorOverview session={sessionStub} caseClient={client} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-empty")).toHaveTextContent(
      "Metrics unavailable",
    );
    expect(screen.getByTestId("state-empty")).toHaveTextContent(
      "Supervisor dashboard port not available",
    );
    expect(screen.queryByTestId("supervisor-kpi-row")).not.toBeInTheDocument();
  });
});
