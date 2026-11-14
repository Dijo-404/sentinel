import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { createCaseApiStub } from "@/adapters/fixture-case-client";
import { EscalationsPanel } from "@/components/ops/escalations-panel";
import { HistoryPanel } from "@/components/ops/history-panel";
import { AuditPanel } from "@/components/ops/audit-panel";
import type { CaseClient } from "@/application/ports";
import { CONTRACT_VERSION, type Case } from "@/domain/types";

const escalatedCase: Case = {
  contract_version: CONTRACT_VERSION,
  case_id: "case-escalated-1",
  revision: 3,
  status: "ESCALATED",
  language: "en-IN",
  intent: "REFUND",
  evidence_ids: [],
};

function withEscalatedCases(base: CaseClient): CaseClient {
  return {
    ...base,
    listOpsCases: async (query) => {
      if (query?.status === "ESCALATED") {
        return { cases: [escalatedCase] };
      }
      return base.listOpsCases(query);
    },
  };
}

describe("supervisor escalations page", () => {
  it("never shows stub copy; list region when fetch succeeds", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={withEscalatedCases(createCaseApiStub("valid"))}
      >
        <EscalationsPanel basePath="/supervisor" />
      </ShellProvider>,
    );

    expect(screen.getByTestId("supervisor-escalations")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(
      await screen.findByTestId("supervisor-escalations-list"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("escalation-link-case-escalated-1")).toHaveAttribute(
      "href",
      "/supervisor/cases/case-escalated-1",
    );
  });

  it("peer failure shows peer-error — no stub copy", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
        caseClient={createCaseApiStub("unavailable")}
      >
        <EscalationsPanel basePath="/supervisor" />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("supervisor-escalations-list"),
    ).not.toBeInTheDocument();
  });

  it("empty escalated list stays honest — no stub copy", async () => {
    const empty = createCaseApiStub("valid");
    empty.listOpsCases = async () => ({ cases: [] });
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={empty}
      >
        <EscalationsPanel basePath="/supervisor" />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("supervisor-escalations")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("state-empty")).toBeInTheDocument();
  });
});

describe("supervisor history page", () => {
  it("never shows stub copy; list region when fetch succeeds", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={createCaseApiStub("valid")}
      >
        <HistoryPanel />
      </ShellProvider>,
    );

    expect(screen.getByTestId("supervisor-history")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(
      await screen.findByTestId("supervisor-history-list"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("history-link-case-demo-history-1")).toHaveAttribute(
      "href",
      "/supervisor/cases/case-demo-history-1",
    );
  });

  it("peer failure shows peer-error — no stub copy", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
        caseClient={createCaseApiStub("unavailable")}
      >
        <HistoryPanel />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("supervisor-history-list"),
    ).not.toBeInTheDocument();
  });

  it("empty history list stays honest — no stub copy", async () => {
    const empty = createCaseApiStub("valid");
    empty.listOpsCases = async () => ({ cases: [] });
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={empty}
      >
        <HistoryPanel />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("supervisor-history")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("state-empty")).toBeInTheDocument();
  });
});

describe("supervisor audit page", () => {
  it("never shows stub copy; audit region when fetch succeeds; no decide controls", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={createCaseApiStub("valid")}
      >
        <AuditPanel />
      </ShellProvider>,
    );

    expect(screen.getByTestId("supervisor-audit")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(
      await screen.findByTestId("supervisor-audit-list"),
    ).toBeInTheDocument();
    expect(screen.getByText("STATUS_CHANGED")).toBeInTheDocument();
    expect(screen.getByText("case-demo-42")).toBeInTheDocument();
    expect(screen.getByText("2026-11-13T12:00:30Z")).toBeInTheDocument();
    expect(screen.queryByTestId("supervisor-decision-workspace")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve|reject|decide/i })).not.toBeInTheDocument();
  });

  it("peer failure shows peer-error — no stub copy", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
        caseClient={createCaseApiStub("unavailable")}
      >
        <AuditPanel />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("supervisor-audit-list"),
    ).not.toBeInTheDocument();
  });

  it("empty audit list stays honest — no stub copy", async () => {
    const empty = createCaseApiStub("valid");
    empty.listOpsAuditEvents = async () => ({ events: [] });
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={empty}
      >
        <AuditPanel />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("supervisor-audit")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("state-empty")).toBeInTheDocument();
  });
});
