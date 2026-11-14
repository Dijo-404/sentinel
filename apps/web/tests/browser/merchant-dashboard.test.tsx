import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MerchantOverview } from "@/components/dashboards/merchant-overview";
import type { AuthSession } from "@/lib/server/auth";

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
  },
  workspaces: [],
} satisfies AuthSession;

describe("merchant dashboard viz", () => {
  it("renders merchant-dashboard with fixture banner and unavailable metrics — no fake KPIs", () => {
    render(<MerchantOverview session={sessionStub} />);

    expect(screen.getByTestId("merchant-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("fixture-banner")).toHaveTextContent(
      "Simulator / fixture — not live production metrics",
    );
    expect(screen.getByTestId("state-empty")).toHaveTextContent(
      "Merchant metrics unavailable",
    );
    expect(screen.queryByText("Captured volume")).not.toBeInTheDocument();
    expect(screen.queryByText("$128,400")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chart-card")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /approve|execute/i }),
    ).toBeNull();
  });
});
