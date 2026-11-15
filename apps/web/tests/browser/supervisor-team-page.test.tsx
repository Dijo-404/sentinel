import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { TeamPanel } from "@/components/ops/team-panel";
import { createOpsTeamStub } from "../stubs/ops-team";

describe("supervisor team page", () => {
  it("never shows stub copy; lists roster when fetch succeeds", async () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <TeamPanel opsTeamClient={createOpsTeamStub("valid")} />
      </ShellProvider>,
    );

    expect(screen.getByTestId("supervisor-team")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId("supervisor-team-list")).toBeInTheDocument();
    expect(screen.getByText("user-supervisor-demo")).toBeInTheDocument();
    expect(screen.getByText("supervisor@example.test")).toBeInTheDocument();
    expect(screen.getByText("operator@example.test")).toBeInTheDocument();
  });

  it("peer failure shows peer-error — no stub copy", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <TeamPanel opsTeamClient={createOpsTeamStub("unavailable")} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(screen.queryByTestId("supervisor-team-list")).not.toBeInTheDocument();
    expect(screen.queryByText("user-supervisor-demo")).not.toBeInTheDocument();
  });

  it("empty roster is honest empty — no invented rows", async () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <TeamPanel opsTeamClient={createOpsTeamStub("empty")} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-empty")).toBeInTheDocument();
    expect(screen.queryByText("user-supervisor-demo")).not.toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
  });
});
