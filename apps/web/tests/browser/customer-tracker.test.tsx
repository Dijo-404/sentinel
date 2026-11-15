import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RefundTracker, customerCopy } from "@/components/customer/refund-tracker";
import type { CaseState } from "@/domain/types";

describe("customerCopy", () => {
  it("only says the money is back once credit is verified", () => {
    const states: CaseState[] = [
      "RECEIVED",
      "NEEDS_INPUT",
      "INVESTIGATING",
      "WAITING_APPROVAL",
      "EXECUTING",
      "VERIFYING",
      "ESCALATED",
      "VERIFIED_RESOLVED",
      "CLOSED_NO_ACTION",
    ];
    const back = states.filter((s) => /money is back/i.test(customerCopy(s).headline));
    expect(back).toEqual(["VERIFIED_RESOLVED"]);
    expect(customerCopy("EXECUTING").headline).toMatch(/on its way/i);
  });
});

describe("RefundTracker", () => {
  it("marks the current step and exposes the status", () => {
    render(
      <RefundTracker
        row={{ case_id: "case-9", status: "EXECUTING", revision: 4, language: "en-IN" }}
      />,
    );
    expect(screen.getByRole("article", { name: /case-9/ })).toBeInTheDocument();
    expect(screen.getByText("Sent to bank").closest("li")).toHaveAttribute("aria-current", "step");
  });
});
