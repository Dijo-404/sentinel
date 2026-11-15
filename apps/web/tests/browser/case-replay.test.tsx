import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { CaseReplay, phaseFor } from "@/components/ledger/case-replay";
import { freshness } from "@/components/ledger/evidence-freshness";
import type { CaseEvent, CaseState } from "@/domain/types";

const ev = (sequence: number, status: CaseState): CaseEvent => ({
  event_id: `e${sequence}`,
  sequence,
  case_id: "case-1",
  case_revision: sequence,
  type: `status.${status.toLowerCase()}`,
  occurred_at: `2026-11-15T10:0${sequence}:00Z`,
  payload: { status, evidence_ids: [], reason_code: "TEST" },
});

describe("phaseFor", () => {
  it("only verified resolution reaches the customer", () => {
    const all: CaseState[] = ["RECEIVED", "NEEDS_INPUT", "INVESTIGATING", "RECONCILING", "PLANNING", "POLICY_CHECK", "WAITING_APPROVAL", "EXECUTING", "VERIFYING", "WAITING_EXTERNAL", "ESCALATED", "VERIFIED_RESOLVED", "CLOSED_NO_ACTION"];
    const atCustomer = all.filter((s) => phaseFor(s).money === "customer");
    expect(atCustomer).toEqual(["VERIFIED_RESOLVED"]);
    expect(phaseFor("VERIFYING").caption).not.toMatch(/verified/i);
    expect(phaseFor("ESCALATED").caption).toMatch(/not resolved/);
  });
});

describe("CaseReplay", () => {
  it("starts on the newest event and scrubs back through history", () => {
    render(<CaseReplay events={[ev(3, "EXECUTING"), ev(1, "RECEIVED"), ev(2, "WAITING_APPROVAL")]} />);
    expect(screen.getByText("step 3 / 3")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /pending is not proof/ })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("slider", { name: "Replay position" }), { target: { value: "0" } });
    expect(screen.getByText("step 1 / 3")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Money with merchant/ })).toBeInTheDocument();
  });
});

describe("freshness", () => {
  const e = { observed_at: "2026-11-15T00:00:00Z", expires_at: "2026-11-18T00:00:00Z" };
  it("reports share of the validity window used and expiry", () => {
    expect(freshness(e, new Date("2026-11-15T12:00:00Z"))).toMatchObject({ state: "fresh", left: "2d 12h left" });
    expect(freshness(e, new Date("2026-11-17T12:00:00Z")).state).toBe("expiring");
    expect(freshness(e, new Date("2026-11-19T00:00:00Z"))).toMatchObject({ state: "expired", used: 1 });
  });
});
