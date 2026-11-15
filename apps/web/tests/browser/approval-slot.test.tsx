import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { ApprovalSlot } from "@/slots/approval-slot";
import { createApprovalUiStub } from "../stubs/approval-ui";

describe("ApprovalSlot mode selection", () => {
  it("fixture mode keeps local substitute data-slot", () => {
    const ok = createApprovalUiStub("valid");
    expect(ok.status).toBe("ok");
    if (ok.status !== "ok") return;
    render(
      <ApprovalSlot state="ready" props={ok.props} mode="fixture" reviewerId="supervisor-demo-1" />,
    );
    expect(screen.getByTestId("approval-slot")).toHaveAttribute(
      "data-slot",
      "approval-ui.v1-local",
    );
    expect(screen.getByText(/local substitute/i)).toBeInTheDocument();
  });

  it("real-peers mounts ApprovalPanel without local substitute slot", () => {
    const ok = createApprovalUiStub("valid");
    expect(ok.status).toBe("ok");
    if (ok.status !== "ok") return;
    render(
      <ApprovalSlot
        state="ready"
        props={ok.props}
        mode="real-peers"
        reviewerId="supervisor-demo-1"
        now={() => new Date("2026-11-13T12:00:00Z")}
      />,
    );
    expect(screen.queryByTestId("approval-slot")).not.toBeInTheDocument();
    expect(screen.queryByText(/local substitute/i)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Approval required" })).toBeInTheDocument();
    expect(screen.getByTestId("approve")).toBeInTheDocument();
    expect(screen.getByTestId("decision-expires-at")).toHaveTextContent("2026-12-31T23:59:59Z");
  });

  it("ShellProvider real-peers supplies mode when ApprovalSlot omits prop", () => {
    const ok = createApprovalUiStub("valid");
    expect(ok.status).toBe("ok");
    if (ok.status !== "ok") return;
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <ApprovalSlot state="ready" props={ok.props} now={() => new Date("2026-11-13T12:00:00Z")} />
      </ShellProvider>,
    );
    expect(screen.queryByTestId("approval-slot")).not.toBeInTheDocument();
    expect(screen.queryByText(/local substitute/i)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Approval required" })).toBeInTheDocument();
  });

  it("real-peers decide stays on injected case-api decide (BFF path)", async () => {
    const decide = vi.fn(async () => ({
      approval_id: "approval-demo-1",
      action_digest: "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
      case_revision: 1,
      policy_version: "demo-policy-v1",
      decision: "APPROVE" as const,
      reviewer_id: "supervisor-demo-1",
      expires_at: "2026-12-31T23:59:59Z",
    }));
    const ok = createApprovalUiStub("valid", decide);
    expect(ok.status).toBe("ok");
    if (ok.status !== "ok") return;
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(
      <ApprovalSlot
        state="ready"
        props={ok.props}
        mode="real-peers"
        reviewerId="supervisor-demo-1"
        now={() => new Date("2026-11-13T12:00:00Z")}
      />,
    );
    await user.click(screen.getByTestId("approve"));
    expect(decide).toHaveBeenCalledWith(
      "action-demo-1",
      expect.objectContaining({
        decision: "APPROVE",
        expires_at: "2026-12-31T23:59:59Z",
      }),
    );
  });
});
