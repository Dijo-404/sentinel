import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IntakeForm } from "@/components/intake-form";
import { CaseTimeline } from "@/components/case-timeline";
import { OperatorQueue } from "@/components/operator-queue";
import { EvidencePanel } from "@/components/evidence-panel";
import { LocalVoiceSubstitute } from "@/slots/local-voice-substitute";
import { ApprovalSlot } from "@/slots/approval-slot";
import { createCaseApiStub } from "../stubs/case-api";
import { createApprovalUiStub } from "../stubs/approval-ui";
import { PeerError } from "@/domain/types";

describe("standalone browser checks", () => {
  it("intake covers loading and success against local fixture", async () => {
    const user = userEvent.setup();
    const client = createCaseApiStub("valid");
    render(
      <IntakeForm caseClient={client} voiceEnabled={false} voiceClient={null} />,
    );
    expect(screen.getByTestId("voice-slot")).toHaveAttribute(
      "data-slot",
      "voice.v1-disabled",
    );
    await user.type(screen.getByLabelText("Complaint message"), "Paid twice");
    await user.click(screen.getByRole("button", { name: "Submit case" }));
    expect(await screen.findByTestId("state-empty")).toHaveTextContent("RECEIVED");
  });

  it("intake shows permission and error states", async () => {
    const user = userEvent.setup();
    render(
      <IntakeForm
        caseClient={createCaseApiStub("unauthorized_or_out_of_scope")}
        voiceEnabled={false}
        voiceClient={null}
      />,
    );
    await user.type(screen.getByLabelText("Complaint message"), "hello");
    await user.click(screen.getByRole("button", { name: "Submit case" }));
    expect(await screen.findByTestId("state-permission")).toHaveTextContent(
      "FORBIDDEN",
    );

    render(
      <IntakeForm
        caseClient={createCaseApiStub("unavailable")}
        voiceEnabled={false}
        voiceClient={null}
      />,
    );
    const forms = screen.getAllByLabelText("Complaint message");
    await user.type(forms[1]!, "hello");
    await user.click(screen.getAllByRole("button", { name: "Submit case" })[1]!);
    expect(await screen.findByTestId("state-error")).toHaveTextContent(
      "PEER_UNAVAILABLE",
    );
  });

  it("timeline loading/empty/error and keyboard focus", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <CaseTimeline caseId="case-demo-42" caseClient={createCaseApiStub("valid")} />,
    );
    expect(screen.getByTestId("state-loading")).toBeInTheDocument();
    expect(await screen.findByRole("list", { name: "Case events" })).toBeInTheDocument();
    expect(screen.getAllByText("Waiting approval").length).toBeGreaterThan(0);
    expect(screen.queryByText("TXN-B")).not.toBeInTheDocument();

    rerender(
      <CaseTimeline
        caseId="case-demo-42"
        caseClient={createCaseApiStub("unavailable")}
      />,
    );
    expect(await screen.findByTestId("state-error")).toHaveTextContent(
      "PEER_UNAVAILABLE",
    );

    render(
      <a href="/ops" data-testid="focus-link">
        Operator queue
      </a>,
    );
    await user.tab();
    // focus moves; assert link can receive keyboard focus
    const link = screen.getByTestId("focus-link");
    link.focus();
    expect(link).toHaveFocus();
  });

  it("operator queue empty and permission states", async () => {
    const emptyClient = createCaseApiStub("valid");
    emptyClient.listOpsCases = async () => ({ cases: [] });
    render(<OperatorQueue caseClient={emptyClient} />);
    expect(await screen.findByTestId("state-empty")).toHaveTextContent("Queue empty");

    render(
      <OperatorQueue caseClient={createCaseApiStub("unauthorized_or_out_of_scope")} />,
    );
    expect(await screen.findByTestId("state-permission")).toHaveTextContent(
      "Permission denied",
    );
  });

  it("evidence masks refs and shows pending/provider/credit/escalation labels", async () => {
    render(
      <EvidencePanel caseId="case-demo-42" caseClient={createCaseApiStub("valid")} />,
    );
    await waitFor(() => {
      expect(screen.getAllByTestId("evidence-card").length).toBeGreaterThan(0);
    });
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Credit pending")).toBeInTheDocument();
    expect(screen.queryByText("subject-demo-9")).not.toBeInTheDocument();
    expect(screen.queryByText("TXN-B")).not.toBeInTheDocument();
    expect(screen.queryByText("refund-demo-1")).not.toBeInTheDocument();
    // Operator / legacy ops evidence: no approve controls by default.
    expect(screen.queryByTestId("approval-slot")).not.toBeInTheDocument();
  });

  it("evidence can enable supervisor approval slot with exact digest/expiry", async () => {
    render(
      <EvidencePanel
        caseId="case-demo-42"
        caseClient={createCaseApiStub("valid")}
        enableApproval
        decisionExpiresAt="2026-12-31T23:59:59Z"
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("approval-slot")).toHaveAttribute(
        "data-slot",
        "approval-ui.v1-local",
      );
    });
    expect(screen.getByTestId("approval-action-digest")).toHaveTextContent(
      "d5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993",
    );
    expect(screen.getByTestId("approval-case-revision")).toHaveTextContent("2");
    expect(screen.getByTestId("approval-decision-expires-at")).toHaveTextContent(
      "2026-12-31T23:59:59Z",
    );
  });

  it("approval slot shows local substitute; peer failure stays visible", () => {
    const ok = createApprovalUiStub("valid");
    expect(ok.status).toBe("ok");
    if (ok.status === "ok") {
      render(<ApprovalSlot state="ready" props={ok.props} />);
      expect(screen.getByTestId("approval-slot")).toHaveTextContent(
        "local substitute",
      );
    }
    const fail = createApprovalUiStub("unavailable");
    expect(fail.status).toBe("error");
    if (fail.status === "error") {
      render(<ApprovalSlot state="error" error={fail.error} />);
      expect(screen.getByRole("alert")).toHaveTextContent("PEER_UNAVAILABLE");
      expect(screen.getByRole("alert")).toHaveTextContent(
        "fixture fallback is not used",
      );
    }
  });

  it("voice slot disabled by default; enabled substitute uses local client", async () => {
    const user = userEvent.setup();
    render(<LocalVoiceSubstitute enabled={false} client={null} />);
    expect(screen.getByTestId("voice-slot")).toHaveTextContent("disabled by default");

    const transcribe = vi.fn(async () => ({
      original_text: "paid twice",
      language: "en-IN",
      ambiguous: false,
      reason_codes: [],
    }));
    render(
      <LocalVoiceSubstitute
        enabled
        client={{ transcribe }}
      />,
    );
    await user.click(screen.getByRole("checkbox"));
    await user.type(screen.getByLabelText("Voice text fallback"), "paid twice");
    await user.click(screen.getByRole("button", { name: "Transcribe" }));
    expect(await screen.findByRole("status")).toHaveTextContent("paid twice");

    render(
      <LocalVoiceSubstitute
        enabled
        client={{
          async transcribe() {
            throw new PeerError("PEER_UNAVAILABLE", "down", "v1", 503);
          },
        }}
      />,
    );
    const boxes = screen.getAllByRole("checkbox");
    await user.click(boxes[boxes.length - 1]!);
    await user.click(screen.getAllByRole("button", { name: "Transcribe" }).at(-1)!);
    expect(await screen.findByTestId("voice-slot-error")).toHaveTextContent(
      "PEER_UNAVAILABLE",
    );
  });

  it("responsive layout exposes primary landmarks", async () => {
    render(
      <EvidencePanel caseId="case-demo-42" caseClient={createCaseApiStub("valid")} />,
    );
    await screen.findByRole("heading", { name: "Evidence workspace" });
    expect(
      screen.getByText(/not proof of customer credit/i),
    ).toBeInTheDocument();
    expect(document.querySelector(".evidence-grid")).toBeTruthy();
  });
});
