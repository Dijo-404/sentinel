import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import MerchantTransactionsPage from "@/app/merchant/(protected)/transactions/page";
import MerchantRefundsPage from "@/app/merchant/(protected)/refunds/page";
import CustomerTransactionsPage from "@/app/customer/(protected)/transactions/page";

describe("transaction / refund list honesty — no hardcoded product rows", () => {
  it("merchant transactions always fail closed — no synthetic rows", () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <MerchantTransactionsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("state-error")).toHaveTextContent(
      "Transactions unavailable",
    );
    expect(screen.queryByText("txn-…2001")).not.toBeInTheDocument();
  });

  it("merchant refunds always fail closed — no synthetic rows", () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "real-peers" })}
      >
        <MerchantRefundsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("state-error")).toHaveTextContent(
      "Refund list unavailable",
    );
    expect(screen.queryByText("refund-req-demo-1")).not.toBeInTheDocument();
  });

  it("customer transactions always fail closed — no synthetic rows", () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <CustomerTransactionsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("state-error")).toHaveTextContent(
      "Transactions unavailable",
    );
    expect(screen.queryByText("txn-…1001")).not.toBeInTheDocument();
  });
});
