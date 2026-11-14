import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { ActivityPanel } from "@/components/ops/activity-panel";
import { createOpsActivityStub } from "../stubs/ops-activity";

describe("operator activity page", () => {
  it("never shows stub copy; lists activity when fetch succeeds", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <ActivityPanel activityClient={createOpsActivityStub("valid")} />
      </ShellProvider>,
    );

    expect(screen.getByTestId("operator-activity")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(
      await screen.findByTestId("operator-activity-list"),
    ).toBeInTheDocument();
    expect(screen.getByText("act-seed-case-demo-42")).toBeInTheDocument();
    expect(
      screen.getByText("Sandbox case case-demo-42 opened"),
    ).toBeInTheDocument();
  });

  it("peer failure shows peer-error — no stub copy", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <ActivityPanel
          activityClient={createOpsActivityStub("unavailable")}
        />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("operator-activity-list"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("act-seed-case-demo-42")).not.toBeInTheDocument();
  });

  it("empty feed is honest empty — no invented rows", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <ActivityPanel activityClient={createOpsActivityStub("empty")} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-empty")).toBeInTheDocument();
    expect(screen.queryByText("act-seed-case-demo-42")).not.toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });
});
