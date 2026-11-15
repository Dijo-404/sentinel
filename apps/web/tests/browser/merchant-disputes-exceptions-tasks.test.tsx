import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { DisputesPanel } from "@/components/merchant/disputes-panel";
import { ExceptionsPanel } from "@/components/merchant/exceptions-panel";
import MerchantTasksPage from "@/app/merchant/(protected)/tasks/page";
import type { AuthSession } from "@/lib/server/auth";
import { createMerchantDisputesStub } from "../stubs/merchant-disputes";
import { createMerchantInboxStub } from "../stubs/merchant-inbox";

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
    scope: { merchant_id: "merchant-demo" },
  },
  workspaces: [],
} satisfies AuthSession;

describe("merchant disputes / exceptions / tasks", () => {
  it("disputes: list region when fetch succeeds — never stub copy", async () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <DisputesPanel session={sessionStub} disputesClient={createMerchantDisputesStub("valid")} />
      </ShellProvider>,
    );

    expect(screen.getByTestId("merchant-disputes")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("merchant-disputes-list")).toBeInTheDocument();
    expect(screen.getByText("dispute-seed-demo-1")).toBeInTheDocument();
  });

  it("disputes: peer failure shows peer-error", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <DisputesPanel
          session={sessionStub}
          disputesClient={createMerchantDisputesStub("unavailable")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(screen.queryByTestId("merchant-disputes-list")).not.toBeInTheDocument();
  });

  it("exceptions: list region when fetch succeeds — never stub copy", async () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <ExceptionsPanel session={sessionStub} inboxClient={createMerchantInboxStub("valid")} />
      </ShellProvider>,
    );

    expect(screen.getByTestId("merchant-exceptions")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("merchant-exceptions-list")).toBeInTheDocument();
    expect(screen.getByText("exc-paid-unfulfilled-1")).toBeInTheDocument();
  });

  it("exceptions: peer failure shows peer-error", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <ExceptionsPanel
          session={sessionStub}
          inboxClient={createMerchantInboxStub("unavailable")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });

  it("tasks: fail closed — inbox has no tasks list; no invented rows", () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <MerchantTasksPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("merchant-tasks")).toBeInTheDocument();
    expect(screen.getByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("tasks: fixture also fail closed — no synthetic SLA rows", () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <MerchantTasksPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("merchant-tasks")).toBeInTheDocument();
    expect(screen.getByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });
});
