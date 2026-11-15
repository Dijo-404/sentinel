import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { KnowledgePanel } from "@/components/ops/knowledge-panel";
import { createKnowledgeStub } from "../stubs/knowledge";

describe("operator knowledge page", () => {
  it("never shows stub copy; lists articles when fetch succeeds", async () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <KnowledgePanel knowledgeClient={createKnowledgeStub("valid")} />
      </ShellProvider>,
    );

    expect(screen.getByTestId("operator-knowledge")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("operator-knowledge-list")).toBeInTheDocument();
    expect(screen.getByText("Sandbox refund policy")).toBeInTheDocument();
    expect(screen.getByText("article-demo-refund-policy")).toBeInTheDocument();
  });

  it("peer failure shows peer-error — no stub copy", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <KnowledgePanel knowledgeClient={createKnowledgeStub("unavailable")} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(screen.queryByTestId("operator-knowledge-list")).not.toBeInTheDocument();
    expect(screen.queryByText("Sandbox refund policy")).not.toBeInTheDocument();
  });

  it("empty articles is honest empty — no invented rows", async () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <KnowledgePanel knowledgeClient={createKnowledgeStub("empty")} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-empty")).toBeInTheDocument();
    expect(screen.queryByText("Sandbox refund policy")).not.toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });
});
