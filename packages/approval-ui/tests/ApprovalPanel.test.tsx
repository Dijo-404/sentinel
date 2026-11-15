import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApprovalPanel } from "../src/ui/ApprovalPanel.js";
import type { ActionRecord, Case, Evidence } from "../src/domain/types.js";
import previewBundle from "../fixtures/preview-bundle.json";
import { createCaseApiStub } from "./stubs/case-api.js";
import { createActionLedgerStub } from "./stubs/action-ledger.js";

const baseProps = {
  case: previewBundle.case as Case,
  action: previewBundle.action as ActionRecord,
  evidence: previewBundle.evidence as Evidence[],
  reviewerId: previewBundle.reviewer.principal_id,
  decisionExpiresAt: previewBundle.decision_expires_at,
  now: () => new Date(previewBundle.virtual_now),
};

describe("ApprovalPanel browser checks", () => {
  it("renders fixture amount, transaction, policy, ages, digest, expiry, reviewer", () => {
    const stub = createCaseApiStub("valid");
    render(<ApprovalPanel {...baseProps} decide={stub.decide} />);

    expect(screen.getByTestId("amount")).toHaveTextContent("INR 1500.00 (150000 minor)");
    expect(screen.getByTestId("transaction-ref")).toHaveTextContent("TXN-B");
    expect(screen.getByTestId("policy-version")).toHaveTextContent("demo-policy-v1");
    expect(screen.getByTestId("action-digest")).toHaveTextContent(previewBundle.expected_sha256);
    expect(screen.getByTestId("decision-expires-at")).toHaveTextContent("2026-11-13T14:00:00Z");
    expect(screen.getByTestId("reviewer-id")).toHaveTextContent("supervisor-demo-1");
    expect(screen.getByTestId("evidence-age-evidence-payment-b")).toHaveTextContent("age 1h 0m");
    expect(screen.getByTestId("evidence-age-evidence-order")).toHaveTextContent("age 55m 0s");
  });

  it("approve submits the supplied digest and revision", async () => {
    const user = userEvent.setup();
    const decide = vi.fn(createCaseApiStub("valid").decide);
    render(<ApprovalPanel {...baseProps} decide={decide} />);

    await user.click(screen.getByTestId("approve"));

    await waitFor(() => expect(decide).toHaveBeenCalledTimes(1));
    expect(decide).toHaveBeenCalledWith("action-demo-1", {
      decision: "APPROVE",
      action_digest: previewBundle.expected_sha256,
      case_revision: 1,
      policy_version: "demo-policy-v1",
      expires_at: "2026-11-13T14:00:00Z",
    });
    expect(await screen.findByTestId("decision-result")).toHaveTextContent("Recorded APPROVE");
  });

  it("handles expired, stale, unauthorized, cross-tenant, and 409 accessibly", async () => {
    const user = userEvent.setup();
    const cases = [
      ["expired", "expired"],
      ["stale", "stale"],
      ["unauthorized_or_out_of_scope", "not authorized"],
      ["cross_tenant", "tenant or subject scope"],
      ["conflict", "http 409"],
    ] as const;

    for (const [stubCase, needle] of cases) {
      const onRefresh = vi.fn();
      const onConflict = vi.fn();
      const stub = createActionLedgerStub(stubCase);
      const { unmount } = render(
        <ApprovalPanel
          {...baseProps}
          decide={stub.decide}
          onRefresh={onRefresh}
          onConflict={onConflict}
        />,
      );

      await user.click(screen.getByTestId("reject"));
      const alert = await screen.findByRole("alert");
      expect(alert.textContent?.toLowerCase()).toContain(needle);

      if (stubCase === "stale") {
        expect(onRefresh).toHaveBeenCalledWith(
          expect.objectContaining({ kind: "refresh", reason_code: "STALE_REVISION" }),
        );
      }
      if (stubCase === "conflict") {
        expect(onConflict).toHaveBeenCalledWith(
          expect.objectContaining({
            kind: "conflict",
            reason_code: "IDEMPOTENCY_CONFLICT",
            status: 409,
          }),
        );
      }
      unmount();
    }
  });

  it("blocks locally when the decision window is already expired", async () => {
    const user = userEvent.setup();
    const decide = vi.fn();
    render(
      <ApprovalPanel {...baseProps} decide={decide} now={() => new Date("2026-11-13T15:00:00Z")} />,
    );

    await user.click(screen.getByTestId("approve"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/expired/i);
    expect(decide).not.toHaveBeenCalled();
  });
});
