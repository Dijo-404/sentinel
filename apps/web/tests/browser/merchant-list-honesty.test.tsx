import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ShellProvider } from "@/adapters/shell-context";
import { loadShellConfig } from "@/adapters/composition";
import MerchantTransactionsPage from "@/app/merchant/(protected)/transactions/page";
import MerchantRefundsPage from "@/app/merchant/(protected)/refunds/page";

describe("merchant transactions / refunds list honesty", () => {
  it("fixture shows labeled merchant transactions with banner", () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <MerchantTransactionsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("merchant-transactions")).toBeInTheDocument();
    expect(screen.getByTestId("fixture-banner")).toBeInTheDocument();
    expect(screen.getByText("txn-…2001")).toBeInTheDocument();
  });

  it("real-peers merchant transactions fail closed — no synthetic live rows", () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
        })}
      >
        <MerchantTransactionsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("state-error")).toHaveTextContent(
      "Transactions unavailable",
    );
    expect(screen.queryByText("txn-…2001")).not.toBeInTheDocument();
    expect(screen.queryByTestId("fixture-banner")).not.toBeInTheDocument();
  });

  it("fixture shows labeled merchant refunds with banner", () => {
    render(
      <ShellProvider
        config={loadShellConfig({ NEXT_PUBLIC_SHELL_MODE: "fixture" })}
      >
        <MerchantRefundsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("merchant-refunds")).toBeInTheDocument();
    expect(screen.getByTestId("fixture-banner")).toBeInTheDocument();
    expect(screen.getByText("refund-req-demo-1")).toBeInTheDocument();
  });

  it("real-peers merchant refunds fail closed — no synthetic live rows", () => {
    render(
      <ShellProvider
        config={loadShellConfig({
          NEXT_PUBLIC_SHELL_MODE: "real-peers",
        })}
      >
        <MerchantRefundsPage />
      </ShellProvider>,
    );

    expect(screen.getByTestId("state-error")).toHaveTextContent(
      "Refund list unavailable",
    );
    expect(screen.queryByText("refund-req-demo-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("fixture-banner")).not.toBeInTheDocument();
  });
});
