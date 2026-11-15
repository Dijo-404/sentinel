import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import MerchantTransactionsPage from "@/app/merchant/(protected)/transactions/page";
import MerchantRefundsPage from "@/app/merchant/(protected)/refunds/page";
import CustomerTransactionsPage from "@/app/customer/(protected)/transactions/page";

describe("transaction / refund list honesty — labeled sandbox catalog", () => {
  it("merchant transactions show Paytm/simulator seed with evidence label", () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <MerchantTransactionsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("sandbox-evidence-label")).toHaveTextContent("not live bank credit");
    expect(screen.getByText("PAYTM-TXN-A1")).toBeInTheDocument();
    expect(screen.queryByText("txn-…2001")).not.toBeInTheDocument();
    expect(screen.queryByTestId("state-error")).not.toBeInTheDocument();
  });

  it("merchant refunds show Paytm/simulator seed with evidence label", () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "real-peers" })}>
        <MerchantRefundsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("sandbox-evidence-label")).toHaveTextContent("not live bank credit");
    expect(screen.getByText("SNT-REF-PAYTM-001")).toBeInTheDocument();
    expect(screen.queryByText("refund-req-demo-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("state-error")).not.toBeInTheDocument();
  });

  it("customer transactions show Paytm/simulator seed with evidence label", () => {
    render(
      <ShellProvider config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}>
        <CustomerTransactionsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("sandbox-evidence-label")).toHaveTextContent("not live bank credit");
    expect(screen.getByText("PAYTM-TXN-A1")).toBeInTheDocument();
    expect(screen.queryByText("txn-…1001")).not.toBeInTheDocument();
    expect(screen.queryByTestId("state-error")).not.toBeInTheDocument();
  });
});
