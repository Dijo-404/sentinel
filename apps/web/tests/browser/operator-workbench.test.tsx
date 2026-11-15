import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { createCaseApiStub } from "@/adapters/fixture-case-client";
import { OperatorQueue, filterOf } from "@/components/operator-queue";
import { CONTRACT_VERSION, type Case, type CaseState } from "@/domain/types";

const c = (id: string, status: CaseState): Case => ({
  contract_version: CONTRACT_VERSION,
  case_id: id,
  revision: 1,
  status,
  language: "en-IN",
  intent: "DUPLICATE_PAYMENT",
  evidence_ids: [],
});

function client(cases: Case[]) {
  const stub = createCaseApiStub("valid");
  stub.listOpsCases = async () => ({ cases });
  return stub;
}

describe("operator workbench", () => {
  it("maps statuses to filter tabs", () => {
    expect(filterOf(c("a", "INVESTIGATING"))).toBe("work");
    expect(filterOf(c("a", "WAITING_APPROVAL"))).toBe("waiting");
    expect(filterOf(c("a", "EXECUTING"))).toBe("waiting");
    expect(filterOf(c("a", "ESCALATED"))).toBe("escalated");
    expect(filterOf(c("a", "VERIFIED_RESOLVED"))).toBe("done");
  });

  it("filters by tab and moves selection with J/K", async () => {
    render(<OperatorQueue caseClient={client([c("case-a", "INVESTIGATING"), c("case-b", "ESCALATED"), c("case-c", "WAITING_APPROVAL")])} />);
    const table = await screen.findByRole("table", { name: "Operator cases" });
    expect(within(table).getAllByRole("row")).toHaveLength(4);

    fireEvent.keyDown(window, { key: "j" });
    expect(within(table).getAllByRole("row")[2]).toHaveAttribute("aria-selected", "true");

    fireEvent.click(screen.getByRole("tab", { name: /Escalated/ }));
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(screen.getByTestId("timeline-link-case-b")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Selected case preview" })).toHaveTextContent("Escalated");
  });
});
