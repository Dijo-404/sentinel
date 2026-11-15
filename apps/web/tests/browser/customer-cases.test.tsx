import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import { createCaseApiStub } from "@/adapters/fixture-case-client";
import CustomerCasesPage from "@/app/customer/(protected)/cases/page";
import CustomerTransactionsPage from "@/app/customer/(protected)/transactions/page";

describe("customer cases / transactions wiring", () => {
  it("fixture lists customer cases via listCustomerCases", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
        caseClient={createCaseApiStub("valid")}
      >
        <CustomerCasesPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("customer-cases")).toBeInTheDocument();
    expect(await screen.findByText("case-demo-42")).toBeInTheDocument();
    expect(screen.getByText("Waiting approval")).toBeInTheDocument();
    expect(screen.queryByTestId("fixture-banner")).not.toBeInTheDocument();
  });

  it("real-peers case list failure stays visible", async () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
          CASE_API_BASE_URL: "http://127.0.0.1:9",
        })}
        caseClient={createCaseApiStub("unavailable")}
      >
        <CustomerCasesPage />
      </ShellProvider>,
    );

    expect(await screen.findByTestId("state-error")).toHaveTextContent("Cases unavailable");
  });

  it("customer transactions show labeled Paytm/simulator sandbox catalog", () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <CustomerTransactionsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("customer-transactions")).toBeInTheDocument();
    expect(screen.getByTestId("sandbox-evidence-label")).toHaveTextContent("Paytm staging");
    expect(screen.getByText("PAYTM-TXN-A1")).toBeInTheDocument();
    expect(screen.queryByTestId("state-error")).not.toBeInTheDocument();
  });
});
