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
    expect(screen.queryByTestId("supervisor-pipeline")).not.toBeInTheDocument();
  });

  it("real-peers missing case client shows error — never fixtureReady", async () => {
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

  it("fixture mode missing case client may use simulator KPIs", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <SupervisorOverview session={sessionStub} caseClient={null} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("supervisor-kpi-row")).toBeInTheDocument();
    expect(screen.getByTestId("fixture-banner")).toBeInTheDocument();
    expect(screen.getByTestId("supervisor-pipeline")).toBeInTheDocument();
  });
});
