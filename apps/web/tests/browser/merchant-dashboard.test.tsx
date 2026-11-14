import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { MerchantOverview } from "@/components/dashboards/merchant-overview";
import type { AuthSession } from "@/lib/server/auth";
import { createMerchantAnalyticsStub } from "../stubs/merchant-analytics";

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
    email: "merchant@example.test",
    display_name: "Demo Merchant",
    password: "x",
    account_status: "ACTIVE" as const,
    account_class: "staff" as const,
    assignments: [],
  },
  assignment: {
    assignment_id: "a1",
    role: "merchant" as const,
    tenant_id: "t1",
    label: "Acme Merchant",
    scope: { merchant_id: "merchant-demo-1" },
  },
  workspaces: [],
} satisfies AuthSession;

describe("merchant dashboard viz", () => {
  it("fixture mode shows merchant-analytics KPIs with fixture banner", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <MerchantOverview
          session={sessionStub}
          analyticsClient={createMerchantAnalyticsStub("valid")}
        />
      </ShellProvider>,
    );

    expect(screen.getByTestId("merchant-dashboard")).toBeInTheDocument();
    expect(await screen.findByTestId("merchant-kpi-row")).toBeInTheDocument();
    expect(screen.getByTestId("fixture-banner")).toHaveTextContent(
      "Simulator / fixture — not live production metrics",
    );
    expect(screen.getByText("Unresolved")).toBeInTheDocument();
    expect(screen.getByText("INR 1000.00")).toBeInTheDocument();
    expect(screen.queryByText("$128,400")).not.toBeInTheDocument();
  });

  it("real-peers peer failure shows unavailable — no silent fixture fill", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <MerchantOverview
          session={sessionStub}
          analyticsClient={createMerchantAnalyticsStub("unavailable")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-empty")).toHaveTextContent(
      "Merchant metrics unavailable",
    );
    expect(screen.queryByTestId("merchant-kpi-row")).not.toBeInTheDocument();
  });

  it("real-peers without merchant scope fails closed — no fixture merchant_ref", async () => {
    const noScope = {
      ...sessionStub,
      assignment: { ...sessionStub.assignment, scope: undefined },
    };
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <MerchantOverview
          session={noScope}
          analyticsClient={createMerchantAnalyticsStub("valid")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-empty")).toHaveTextContent(
      "no merchant_ref",
    );
    expect(screen.queryByTestId("merchant-kpi-row")).not.toBeInTheDocument();
  });
});
