import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { AssistantPanel } from "@/components/ops/assistant-panel";
import { createAssistantStub } from "../stubs/assistant";

describe("operator assistant page", () => {
  it("never shows stub copy; lists threads when fetch succeeds", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <AssistantPanel
          role="operator"
          testId="operator-assistant"
          assistantClient={createAssistantStub("valid")}
        />
      </ShellProvider>,
    );

    expect(screen.getByTestId("operator-assistant")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(
      await screen.findByTestId("operator-assistant-threads"),
    ).toBeInTheDocument();
    expect(screen.getByText("Operator sandbox thread")).toBeInTheDocument();
    expect(screen.getByText("thr-op-fixture-1")).toBeInTheDocument();
  });

  it("selecting a thread loads messages — no stub copy", async () => {
    const user = userEvent.setup();
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <AssistantPanel
          role="operator"
          testId="operator-assistant"
          assistantClient={createAssistantStub("valid")}
        />
      </ShellProvider>,
    );

    await screen.findByTestId("operator-assistant-threads");
    await user.click(screen.getByTestId("assistant-thread-thr-op-fixture-1"));
    expect(
      await screen.findByTestId("operator-assistant-messages"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Hello from tenant-demo sandbox seed."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
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
          role="operator"
          testId="operator-assistant"
          assistantClient={createAssistantStub("unavailable")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("operator-assistant-threads"),
    ).not.toBeInTheDocument();
  });

  it("empty threads is honest empty — no invented rows", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <AssistantPanel
          role="operator"
          testId="operator-assistant"
          assistantClient={createAssistantStub("empty")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-empty")).toBeInTheDocument();
    expect(
      screen.queryByText("Operator sandbox thread"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });
});
