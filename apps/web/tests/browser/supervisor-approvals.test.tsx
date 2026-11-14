import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SupervisorApprovalsQueue } from "@/components/approvals/supervisor-approvals-queue";
import {
  FIXTURE_DECISION_EXPIRES_AT,
  SupervisorDecisionWorkspace,
} from "@/components/approvals/supervisor-decision-workspace";
import { createCaseApiStub } from "../stubs/case-api";
import { createApprovalUiStub } from "../stubs/approval-ui";

describe("supervisor approvals", () => {
  it("queue lists waiting cases and links to decision workspace", async () => {
    render(
      <SupervisorApprovalsQueue
        caseClient={createCaseApiStub("valid")}
        mode="fixture"
      />,
    );
    expect(await screen.findByTestId("supervisor-approvals")).toBeInTheDocument();
    expect(screen.getByTestId("open-approval-action-demo-1")).toHaveAttribute(
      "href",
      "/supervisor/approvals/action-demo-1",
    );
    expect(screen.getByText(/Fixture mode/i)).toBeInTheDocument();
  });

  it("queue empty and permission states", async () => {
    const empty = createCaseApiStub("valid");
    empty.listOpsCases = async () => ({ cases: [] });
    render(<SupervisorApprovalsQueue caseClient={empty} mode="fixture" />);
    expect(await screen.findByTestId("state-empty")).toHaveTextContent("Queue empty");

    render(
      <SupervisorApprovalsQueue
        caseClient={createCaseApiStub("unauthorized_or_out_of_scope")}
        mode="fixture"
      />,
    );
    expect(await screen.findByTestId("state-permission")).toHaveTextContent(
      "Permission denied",
    );
  });

  it("decision workspace embeds local substitute and posts exact decide payload", async () => {
    const user = userEvent.setup();
    const client = createCaseApiStub("valid");
    const decide = vi.fn(client.decide.bind(client));
    client.decide = decide;

    render(
      <SupervisorDecisionWorkspace
        actionId="action-demo-1"
        caseClient={client}
        mode="fixture"
      />,
    );

    await waitFor(() => {
      expect(screen.getByTestId("supervisor-decision-workspace")).toBeInTheDocument();
    });
    expect(screen.getByTestId("approval-slot")).toHaveAttribute(
      "data-slot",
      "approval-ui.v1-local",
    );
    expect(screen.getByTestId("approval-action-digest")).toHaveTextContent(
      "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
    );
    expect(screen.getByTestId("approval-case-revision")).toHaveTextContent("2");
    expect(screen.getByTestId("approval-decision-expires-at")).toHaveTextContent(
      FIXTURE_DECISION_EXPIRES_AT,
    );

    await user.click(screen.getByTestId("approval-approve"));
    await waitFor(() => {
      expect(decide).toHaveBeenCalledWith("action-demo-1", {
        decision: "APPROVE",
        action_digest:
          "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
        case_revision: 2,
        policy_version: "demo-policy-v1",
        expires_at: FIXTURE_DECISION_EXPIRES_AT,
      });
    });
    expect(
      await screen.findByText(/Decision recorded: APPROVE/),
    ).toBeInTheDocument();
  });

  it("decision workspace surfaces approval peer failure without fixture fallback", async () => {
    const fail = createApprovalUiStub("unavailable");
    expect(fail.status).toBe("error");
    if (fail.status !== "error") return;
    render(
      <SupervisorDecisionWorkspace
        actionId="action-demo-1"
        caseClient={createCaseApiStub("valid")}
        mode="real-peers"
        approvalSlot={{ state: "error", error: fail.error }}
      />,
    );
    expect(await screen.findByTestId("supervisor-decision-workspace")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("PEER_UNAVAILABLE");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "fixture fallback is not used",
    );
    expect(screen.queryByTestId("approval-approve")).not.toBeInTheDocument();
  });
});
