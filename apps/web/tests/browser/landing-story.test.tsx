import { describe, expect, it } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import {
  advance,
  checkStates,
  inject,
  isResolved,
  limitCheck,
} from "@/components/marketing/landing/model";
import { LandingPage } from "@/components/marketing/landing-page";

describe("landing simulator model", () => {
  it("only resolves after all five stages with no fault", () => {
    let s = { step: 0, fault: null } as Parameters<typeof advance>[0];
    for (let i = 0; i < 5; i++) s = advance(s);
    expect(isResolved(s)).toBe(true);
    expect(checkStates(s).every((c) => c.ok)).toBe(true);
  });

  it("a fault blocks advancing and fails the matching check", () => {
    const s = inject({ step: 0, fault: null }, "edited");
    expect(advance(s)).toBe(s);
    expect(isResolved(s)).toBe(false);
    expect(checkStates(s).find((c) => !c.ok)?.code).toMatch(/^sha256/);
  });

  it("limit counts completed + pending + reserved", () => {
    expect(limitCheck(70000, 128000, 200000)).toMatchObject({ allowed: true, after: 2000 });
    expect(limitCheck(80000, 128000, 200000)).toMatchObject({ allowed: false, over: 8000 });
  });
});

describe("landing interactions", () => {
  it("injecting a provider timeout explains reconcile-not-resend", () => {
    render(<LandingPage />);
    const sim = document.getElementById("simulator")!;
    fireEvent.click(within(sim).getByRole("button", { name: /Provider timeout/ }));
    expect(within(sim).getByText("RECONCILE · NOT RESEND")).toBeInTheDocument();
    expect(within(sim).getByRole("button", { name: "Clear the fault to continue" })).toBeDisabled();
  });

  it("guardrail picker shows which layer blocks the attempt", () => {
    render(<LandingPage />);
    fireEvent.click(screen.getByRole("radio", { name: /Send money to a new bank account/ }));
    const blocked = screen.getByText("BLOCKED").closest("li")!;
    expect(blocked).toHaveTextContent("Original payment route");
  });
});
