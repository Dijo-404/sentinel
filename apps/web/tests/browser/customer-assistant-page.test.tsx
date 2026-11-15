import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { AssistantPanel } from "@/components/ops/assistant-panel";
import { createAssistantStub } from "../stubs/assistant";

describe("customer assistant page", () => {
  it("never shows stub copy; lists customer threads when fetch succeeds", async () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <AssistantPanel
          role="customer"
          testId="customer-assistant"
          assistantClient={createAssistantStub("valid")}
        />
      </ShellProvider>,
    );

    expect(screen.getByTestId("customer-assistant")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("customer-assistant-threads")).toBeInTheDocument();
    expect(screen.getByText("Sandbox assistant thread")).toBeInTheDocument();
    expect(screen.getByText("thr-seed-tenant-demo")).toBeInTheDocument();
  });

  it("peer failure shows peer-error — no stub copy", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <AssistantPanel
          role="customer"
          testId="customer-assistant"
          assistantClient={createAssistantStub("unavailable")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(screen.queryByTestId("customer-assistant-threads")).not.toBeInTheDocument();
    expect(screen.queryByText("Sandbox assistant thread")).not.toBeInTheDocument();
  });
});
