import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import {
  OperatorOverview,
  projectionStatusSlices,
} from "@/components/dashboards/operator-overview";
import { OperatorQueue } from "@/components/operator-queue";
import { createCaseApiStub } from "../stubs/case-api";
import type { AuthSession } from "@/lib/server/auth";
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

describe("operator dashboard overview", () => {
  it("renders operator-dashboard with KPIs from projection, fixture banner, and chart", async () => {
    render(
      <OperatorOverview
        session={sessionStub}
        caseClient={createCaseApiStub("valid")}
      />,
    );

    expect(await screen.findByTestId("operator-dashboard")).toBeInTheDocument();
    expect(await screen.findByTestId("operator-kpi-row")).toBeInTheDocument();
    expect(screen.getByTestId("fixture-banner")).toHaveTextContent(
      "Simulator / fixture — not live production metrics",
    );
    expect(screen.getByText("Open")).toBeInTheDocument();
    expect(screen.getByText("Waiting")).toBeInTheDocument();
    expect(screen.getByText("Assigned")).toBeInTheDocument();
    expect(screen.getByText("Interventions")).toBeInTheDocument();
    expect(screen.getByTestId("chart-card")).toBeInTheDocument();
    expect(screen.getByTestId("operator-status-chart")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /open full queue/i }),
    ).toHaveAttribute("href", "/operator/queue");
    expect(screen.queryByTestId("approval-slot")).not.toBeInTheDocument();
  });

  it("builds chart slices from projection aggregates", () => {
    const slices = projectionStatusSlices({
      assigned_to_me: 2,
      unassigned: 1,
      escalated: 0,
      waiting_approval: 3,
      open_total: 6,
    });
    expect(slices).toEqual([
      { name: "Assigned to me", value: 2 },
      { name: "Unassigned", value: 1 },
      { name: "Waiting approval", value: 3 },
    ]);
  });

  it("peer failure shows unavailable — never fake KPIs", async () => {
    render(
      <OperatorOverview
        session={sessionStub}
        caseClient={createCaseApiStub("unavailable")}
        mode="fixture"
      />,
    );

    expect(await screen.findByTestId("state-empty")).toHaveTextContent(
      "Metrics unavailable",
    );
    expect(screen.getByTestId("state-empty")).toHaveTextContent(
      "PEER_UNAVAILABLE",
    );
    expect(screen.queryByTestId("operator-kpi-row")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("operator-status-chart"),
    ).not.toBeInTheDocument();
  });

  it("real-peers peer failure shows unavailable — no silent fixture fill", async () => {
    render(
      <OperatorOverview
        session={sessionStub}
        caseClient={createCaseApiStub("unavailable")}
        mode="real-peers"
      />,
    );

    expect(await screen.findByTestId("state-empty")).toHaveTextContent(
      "Metrics unavailable",
    );
    expect(screen.getByTestId("state-empty")).toHaveTextContent(
      "PEER_UNAVAILABLE",
    );
    expect(screen.queryByTestId("fixture-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("operator-kpi-row")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("operator-status-chart"),
    ).not.toBeInTheDocument();
  });

  it("missing dashboard method shows unavailable — never listOpsCases KPIs", async () => {
    const client = createCaseApiStub("valid");
    delete client.getOperatorDashboard;
    render(
      <OperatorOverview
        session={sessionStub}
        caseClient={client}
        mode="real-peers"
      />,
    );

    expect(await screen.findByTestId("state-empty")).toHaveTextContent(
      "Metrics unavailable",
    );
    expect(screen.getByTestId("state-empty")).toHaveTextContent(
      "Operator dashboard port not available",
    );
    expect(screen.queryByTestId("operator-kpi-row")).not.toBeInTheDocument();
  });

  it("zero projection keeps chart empty of slices and shows zeros", async () => {
    const empty = createCaseApiStub("valid");
    empty.getOperatorDashboard = async () => ({
      assigned_to_me: 0,
      unassigned: 0,
      escalated: 0,
      waiting_approval: 0,
      open_total: 0,
    });
    render(
      <OperatorOverview
        session={sessionStub}
        caseClient={empty}
        mode="real-peers"
      />,
    );

    expect(await screen.findByTestId("operator-kpi-row")).toBeInTheDocument();
    expect(screen.queryByTestId("fixture-banner")).not.toBeInTheDocument();
    expect(
      screen.getByText("Case status (scoped projection)"),
    ).toBeInTheDocument();
    const open = screen.getByText("Open").closest("[data-testid=stat-block]");
    expect(open).toHaveTextContent("0");
    expect(open).toHaveTextContent("Scoped projection");
  });
});

describe("operator queue wire", () => {
  it("renders queue without approval-slot and links timeline to operator case route", async () => {
    render(<OperatorQueue caseClient={createCaseApiStub("valid")} />);
    expect(
      await screen.findByRole("table", { name: "Operator cases" }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("approval-slot")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /approve|reject/i }),
    ).toBeNull();
    const timeline = screen.getByTestId("timeline-link-case-demo-42");
    expect(timeline).toHaveAttribute("href", "/operator/cases/case-demo-42");
    expect(timeline.getAttribute("href")).not.toMatch(/^\/cases\//);
  });

  it("paginates with Load more when next_cursor present", async () => {
    const client = createCaseApiStub("valid");
    let page = 0;
    client.listOpsCases = async (query) => {
      if (!query?.after) {
        page = 1;
        return {
          cases: [
            {
              contract_version: CONTRACT_VERSION,
              case_id: "case-page-1",
              revision: 1,
              status: "INVESTIGATING",
              language: "en-IN",
              intent: "DUPLICATE_PAYMENT",
              evidence_ids: [],
            },
          ],
          next_cursor: "case-page-1",
        };
      }
      page = 2;
      return {
        cases: [
          {
            contract_version: CONTRACT_VERSION,
            case_id: "case-page-2",
            revision: 1,
            status: "ESCALATED",
            language: "en-IN",
            intent: "DUPLICATE_PAYMENT",
            evidence_ids: [],
          },
        ],
        next_cursor: undefined,
      };
    };
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<OperatorQueue caseClient={client} />);
    expect(await screen.findByTestId("queue-load-more")).toBeInTheDocument();
    await user.click(screen.getByTestId("queue-load-more"));
    await waitFor(() => {
      expect(page).toBe(2);
      expect(screen.getByTestId("timeline-link-case-page-2")).toBeInTheDocument();
    });
  });
});
