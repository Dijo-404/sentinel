import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { createCaseApiStub } from "@/adapters/fixture-case-client";
import { EscalationsPanel } from "@/components/ops/escalations-panel";
import { MessagesPanel } from "@/components/ops/messages-panel";
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

describe("operator escalations page", () => {
  it("never shows stub copy; list region when fetch succeeds", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={withEscalatedCases(createCaseApiStub("valid"))}
      >
        <EscalationsPanel basePath="/operator" />
      </ShellProvider>,
    );

    expect(screen.getByTestId("operator-escalations")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("operator-escalations-list")).toBeInTheDocument();
    expect(screen.getByTestId("escalation-link-case-escalated-1")).toHaveAttribute(
      "href",
      "/operator/cases/case-escalated-1",
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
        <EscalationsPanel basePath="/operator" />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(screen.queryByTestId("operator-escalations-list")).not.toBeInTheDocument();
  });

  it("empty escalated list stays honest — no stub copy", async () => {
    const empty = createCaseApiStub("valid");
    empty.listOpsCases = async () => ({ cases: [] });
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={empty}
      >
        <EscalationsPanel basePath="/operator" />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("operator-escalations")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("state-empty")).toBeInTheDocument();
  });
});

describe("operator messages page", () => {
  it("never shows stub copy; messages region when fetch succeeds", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={createCaseApiStub("valid")}
      >
        <MessagesPanel />
      </ShellProvider>,
    );

    expect(screen.getByTestId("operator-messages")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("operator-messages-list")).toBeInTheDocument();
    expect(screen.getByText("case-demo-42")).toBeInTheDocument();
    expect(screen.getByText("Customer paid twice for the same order")).toBeInTheDocument();
    expect(screen.getByText("2026-11-13T12:00:00Z")).toBeInTheDocument();
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
        <MessagesPanel />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(screen.queryByTestId("operator-messages-list")).not.toBeInTheDocument();
  });

  it("empty messages list stays honest — no stub copy", async () => {
    const empty = createCaseApiStub("valid");
    empty.listOpsMessages = async () => ({ messages: [] });
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={empty}
      >
        <MessagesPanel />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("operator-messages")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("state-empty")).toBeInTheDocument();
  });
});
