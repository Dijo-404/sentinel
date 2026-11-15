import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { createCaseApiStub } from "@/adapters/fixture-case-client";
import { CommandCenter } from "@/components/ops/command-center";
import { buildCommandModel, hourlyBuckets, incidentReason } from "@/components/ops/command-model";
import { crossesIntoPortal } from "@/app/template";
import { CONTRACT_VERSION, type Case, type CaseState } from "@/domain/types";

const c = (id: string, status: CaseState, revision = 1): Case => ({
  contract_version: CONTRACT_VERSION,
  case_id: id,
  revision,
  status,
  language: "en-IN",
  intent: "refund",
  evidence_ids: [],
});

describe("buildCommandModel", () => {
  it("counts each case once, funnels linear stages, keeps escalation off the path", () => {
    const m = buildCommandModel([
      c("a", "INVESTIGATING", 1),
      c("a", "WAITING_APPROVAL", 2),
      c("b", "EXECUTING"),
      c("d", "VERIFIED_RESOLVED"),
      c("e", "ESCALATED"),
      c("f", "CLOSED_NO_ACTION"),
    ]);
    expect(m.total).toBe(5);
    expect(m.waitingApproval).toBe(1);
    expect(m.inFlight).toBe(1);
    expect(m.verified).toBe(1);
    expect(m.escalated).toBe(1);
    expect(m.reached).toEqual([3, 3, 3, 2, 1, 1]);
  });

  it("buckets audit events per hour and ignores bad timestamps", () => {
    const now = new Date("2026-11-15T12:30:00Z");
    const ev = (t: string) => ({
      case_id: "x",
      sequence: 1,
      type: "t",
      occurred_at: t,
      payload: {},
    });
    const b = hourlyBuckets(
      [
        ev("2026-11-15T12:10:00Z"),
        ev("2026-11-15T10:40:00Z"),
        ev("nope"),
        ev("2026-11-13T00:00:00Z"),
      ],
      now,
    );
    expect(b).toHaveLength(24);
    expect(b[23]).toBe(1);
    expect(b[22]).toBe(1);
    expect(b.reduce((x, y) => x + y, 0)).toBe(2);
  });
});

describe("CommandCenter", () => {
  it("renders live sections from the case client", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={createCaseApiStub("valid")}
      >
        <CommandCenter />
      </ShellProvider>,
    );
    expect(await screen.findByTestId("command-center")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Command center" })).toBeInTheDocument();
    expect(screen.getByText(/Fixture mode/)).toBeInTheDocument();
  });

  it("keeps peer failure visible with no fixture fallback", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
        caseClient={createCaseApiStub("unavailable")}
      >
        <CommandCenter />
      </ShellProvider>,
    );
    expect(await screen.findByText("Command center unavailable")).toBeInTheDocument();
    expect(screen.queryByTestId("command-center")).not.toBeInTheDocument();
  });
});

describe("incident mode + curtain", () => {
  it("trips only on refresh failure or a high escalation share", () => {
    const base = buildCommandModel([
      c("a", "INVESTIGATING"),
      c("b", "EXECUTING"),
      c("d", "VERIFIED_RESOLVED"),
      c("e", "RECEIVED"),
    ]);
    expect(incidentReason(base, false)).toBeNull();
    expect(incidentReason(base, true)).toMatch(/stale/);
    const hot = buildCommandModel([
      c("a", "ESCALATED"),
      c("b", "EXECUTING"),
      c("d", "VERIFIED_RESOLVED"),
      c("e", "RECEIVED"),
    ]);
    expect(incidentReason(hot, false)).toMatch(/25%/);
  });
  it("curtain only when entering a portal from landing or login", () => {
    expect(crossesIntoPortal("/login", "/operator/dashboard")).toBe(true);
    expect(crossesIntoPortal("/", "/customer/cases")).toBe(true);
    expect(crossesIntoPortal("/operator/queue", "/operator/dashboard")).toBe(false);
    expect(crossesIntoPortal(null, "/operator/dashboard")).toBe(false);
    expect(crossesIntoPortal("/login", "/operatorx")).toBe(false);
  });
});
