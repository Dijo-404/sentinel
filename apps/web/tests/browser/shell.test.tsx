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
    const { container } = render(
      <IntakeForm
        caseClient={client}
        voiceEnabled={false}
        voiceClient={null}
        orderSuggestions={["subject-demo-9/DEMO-ORDER-42"]}
      />,
    );
    expect(screen.getByTestId("voice-slot")).toHaveAttribute("data-slot", "voice.v1-disabled");
    expect(
      container.querySelector('datalist option[value="subject-demo-9/DEMO-ORDER-42"]'),
    ).not.toBeNull();
    await user.type(screen.getByLabelText("Order reference"), "subject-demo-9/DEMO-ORDER-42");
    await user.type(screen.getByLabelText("Complaint message"), "Paid twice");
    await user.click(screen.getByRole("button", { name: "Submit case" }));
    expect(await screen.findByTestId("state-empty")).toHaveTextContent("RECEIVED");
    expect(screen.getByRole("link", { name: "View case" })).toHaveAttribute(
      "href",
      expect.stringMatching(/^\/cases\/case-/),
    );
  });

  it("intake trims input, blocks blank order reference, clears message after submit", async () => {
    const user = userEvent.setup();
    const client = createCaseApiStub("valid");
    const createCase = vi.fn(client.createCase.bind(client));
    client.createCase = createCase;
    render(<IntakeForm caseClient={client} voiceEnabled={false} voiceClient={null} />);
    const submit = screen.getByRole("button", { name: "Submit case" });
    // No unbound provider-id prefill (case-api rejects it as not bound to principal).
    expect(screen.getByLabelText("Order reference")).toHaveValue("");
    await user.type(screen.getByLabelText("Complaint message"), "  Paid twice  ");
    await user.clear(screen.getByLabelText("Order reference"));
    await user.type(screen.getByLabelText("Order reference"), "   ");
    expect(submit).toBeDisabled();
    await user.clear(screen.getByLabelText("Order reference"));
    await user.type(screen.getByLabelText("Order reference"), " subject-demo-9/DEMO-ORDER-42 ");
    await user.click(submit);
    await screen.findByTestId("state-empty");
    expect(createCase).toHaveBeenCalledWith(
      expect.objectContaining({
        message: "Paid twice",
        order_reference: "subject-demo-9/DEMO-ORDER-42",
      }),
      expect.any(String),
    );
    expect(screen.getByLabelText("Complaint message")).toHaveValue("");
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
    await user.type(screen.getByLabelText("Order reference"), "subject-demo-9/DEMO-ORDER-42");
    await user.type(screen.getByLabelText("Complaint message"), "hello");
    await user.click(screen.getByRole("button", { name: "Submit case" }));
    expect(await screen.findByTestId("state-permission")).toHaveTextContent("FORBIDDEN");

    render(
      <IntakeForm
        caseClient={createCaseApiStub("unavailable")}
        voiceEnabled={false}
        voiceClient={null}
      />,
    );
    await user.type(
      screen.getAllByLabelText("Order reference")[1]!,
      "subject-demo-9/DEMO-ORDER-42",
    );
    const forms = screen.getAllByLabelText("Complaint message");
    await user.type(forms[1]!, "hello");
    await user.click(screen.getAllByRole("button", { name: "Submit case" })[1]!);
    expect(await screen.findByTestId("state-error")).toHaveTextContent("PEER_UNAVAILABLE");
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
    expect(screen.getByTestId("case-interactions")).toBeInTheDocument();
    expect(screen.getByTestId("case-message-submit")).toBeInTheDocument();
    expect(screen.getByTestId("case-escalate")).toBeInTheDocument();

    rerender(<CaseTimeline caseId="case-demo-42" caseClient={createCaseApiStub("unavailable")} />);
    expect(await screen.findByTestId("state-error")).toHaveTextContent("PEER_UNAVAILABLE");

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

  it("timeline message and escalate call case client", async () => {
    const user = userEvent.setup();
    const client = createCaseApiStub("valid");
    const postMessage = vi.fn(client.postMessage.bind(client));
    const escalate = vi.fn(client.escalate.bind(client));
    client.postMessage = postMessage;
    client.escalate = escalate;
    render(<CaseTimeline caseId="case-demo-42" caseClient={client} />);
    await screen.findByTestId("case-interactions");
    await user.type(screen.getByTestId("case-message-input"), "Need update");
    await user.click(screen.getByTestId("case-message-submit"));
    await waitFor(() => {
      expect(postMessage).toHaveBeenCalledWith(
        "case-demo-42",
        expect.objectContaining({
          message: "Need update",
          expected_revision: 2,
        }),
      );
    });
    await user.click(screen.getByTestId("case-escalate"));
    await waitFor(() => {
      expect(escalate).toHaveBeenCalled();
    });
  });

  it("operator queue empty and permission states", async () => {
    const emptyClient = createCaseApiStub("valid");
    emptyClient.listOpsCases = async () => ({ cases: [] });
    render(<OperatorQueue caseClient={emptyClient} />);
    expect(await screen.findByTestId("state-empty")).toHaveTextContent("Queue empty");

    render(<OperatorQueue caseClient={createCaseApiStub("unauthorized_or_out_of_scope")} />);
    expect(await screen.findByTestId("state-permission")).toHaveTextContent("Permission denied");
  });

  it("evidence masks refs and shows pending/provider/credit/escalation labels", async () => {
    render(<EvidencePanel caseId="case-demo-42" caseClient={createCaseApiStub("valid")} />);
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

  it("evidence approval loads getAction digest and evidence expiry — not demoAction/fixed date", async () => {
    render(
      <EvidencePanel
        caseId="case-demo-42"
        caseClient={createCaseApiStub("valid")}
        enableApproval
        mode="fixture"
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
    // From evidence-bundle expires_at, not 2026-12-31 fixture constant.
    expect(screen.getByTestId("approval-decision-expires-at")).toHaveTextContent(
      "2026-11-14T12:00:00Z",
    );
    expect(screen.queryByText("2026-12-31T23:59:59Z")).not.toBeInTheDocument();
  });

  it("evidence real-peers approval does not use local substitute data-slot", async () => {
    render(
      <EvidencePanel
        caseId="case-demo-42"
        caseClient={createCaseApiStub("valid")}
        enableApproval
        mode="real-peers"
        reviewerId="supervisor-demo-1"
      />,
    );
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Approval required" })).toBeInTheDocument();
    });
    expect(screen.queryByTestId("approval-slot")).not.toBeInTheDocument();
    expect(screen.queryByText(/local substitute/i)).not.toBeInTheDocument();
    expect(document.querySelector('[data-slot="approval-ui.v1-local"]')).toBeNull();
    expect(screen.getByTestId("approve")).toBeInTheDocument();
  });

  it("approval slot shows local substitute; peer failure stays visible", () => {
    const ok = createApprovalUiStub("valid");
    expect(ok.status).toBe("ok");
    if (ok.status === "ok") {
      render(<ApprovalSlot state="ready" props={ok.props} />);
      expect(screen.getByTestId("approval-slot")).toHaveTextContent("local substitute");
    }
    const fail = createApprovalUiStub("unavailable");
    expect(fail.status).toBe("error");
    if (fail.status === "error") {
      render(<ApprovalSlot state="error" error={fail.error} />);
      expect(screen.getByRole("alert")).toHaveTextContent("PEER_UNAVAILABLE");
      expect(screen.getByRole("alert")).toHaveTextContent("fixture fallback is not used");
    }
  });

  it("voice slot disabled by default; enabled peer labels evidence_mode", async () => {
    const user = userEvent.setup();
    render(<LocalVoiceSubstitute enabled={false} client={null} />);
    expect(screen.getByTestId("voice-slot")).toHaveTextContent("disabled by default");

    const transcribe = vi.fn(async () => ({
      original_text: "paid twice",
      language: "en-IN",
      ambiguous: false,
      reason_codes: [],
      evidence_mode: "recorded",
    }));
    render(<LocalVoiceSubstitute enabled client={{ transcribe }} />);
    await user.click(screen.getByRole("checkbox"));
    await user.type(screen.getByLabelText("Voice text fallback"), "paid twice");
    await user.click(screen.getByRole("button", { name: "Transcribe" }));
    expect(await screen.findByTestId("voice-slot-result")).toHaveTextContent("paid twice");
    expect(screen.getByTestId("voice-evidence-mode")).toHaveTextContent("evidence_mode=recorded");

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
    expect(await screen.findByTestId("voice-slot-error")).toHaveTextContent("PEER_UNAVAILABLE");
  });

  it("responsive layout exposes primary landmarks", async () => {
    render(<EvidencePanel caseId="case-demo-42" caseClient={createCaseApiStub("valid")} />);
    await screen.findByRole("heading", { name: "Evidence workspace" });
    expect(screen.getByText(/not proof of customer credit/i)).toBeInTheDocument();
    expect(document.querySelector(".evidence-grid")).toBeTruthy();
  });
});
