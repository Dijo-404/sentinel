import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { RiskPeerPanel } from "@/components/risk/risk-peer-panel";
import { createRiskStub } from "../stubs/risk";

const VIEWS = ["queue", "holds", "transactions", "audit", "analytics", "reports"] as const;

describe("risk peer pages", () => {
  it.each(VIEWS)("%s never shows stub copy; list/metrics when fetch succeeds", async (view) => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <RiskPeerPanel view={view} riskClient={createRiskStub("valid")} />
      </ShellProvider>,
    );

    expect(screen.getByTestId(`risk-${view}`)).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(await screen.findByTestId(`risk-${view}-data`)).toBeInTheDocument();
  });

  it.each(VIEWS)("%s peer failure shows peer-error — no stub copy", async (view) => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
      >
        <RiskPeerPanel view={view} riskClient={createRiskStub("unavailable")} />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("peer-error")).toBeInTheDocument();
    expect(screen.queryByText("Not available yet")).not.toBeInTheDocument();
    expect(screen.queryByTestId(`risk-${view}-data`)).not.toBeInTheDocument();
  });
});
