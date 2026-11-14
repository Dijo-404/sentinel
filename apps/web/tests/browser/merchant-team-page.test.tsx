import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { TeamPanel } from "@/components/merchant/team-panel";
import type { AuthSession } from "@/lib/server/auth";
import { createMerchantTeamsStub } from "../stubs/merchant-teams";

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

describe("merchant team page", () => {
  it("never shows stub copy; lists staff when fetch succeeds", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <TeamPanel
          session={sessionStub}
          teamsClient={createMerchantTeamsStub("valid")}
        />
      </ShellProvider>,
    );

    expect(screen.getByTestId("merchant-team")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("merchant-team-list")).toBeInTheDocument();
    expect(screen.getByText("staff-demo-1")).toBeInTheDocument();
    expect(screen.getByText("Ada Merchant")).toBeInTheDocument();
  });

  it("peer failure shows peer-error — no stub copy", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <TeamPanel
          session={sessionStub}
          teamsClient={createMerchantTeamsStub("unavailable")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(screen.queryByTestId("merchant-team-list")).not.toBeInTheDocument();
    expect(screen.queryByText("staff-demo-1")).not.toBeInTheDocument();
  });

  it("empty team is honest empty — no invented rows", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <TeamPanel
          session={sessionStub}
          teamsClient={createMerchantTeamsStub("empty")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-empty")).toBeInTheDocument();
    expect(screen.queryByText("staff-demo-1")).not.toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });
});
