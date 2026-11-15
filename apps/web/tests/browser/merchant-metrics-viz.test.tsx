import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MerchantMetricsViz, humanDuration, parseRate } from "@/components/merchant/metrics-viz";
import { FIXTURE_MERCHANT_METRICS } from "../stubs/merchant-analytics";

describe("merchant metrics helpers", () => {
  it("parses decimal and percent rates, rejects junk", () => {
    expect(parseRate("0.4000")).toBe(0.4);
    expect(parseRate("4.2%")).toBeCloseTo(0.042);
    expect(parseRate("n/a")).toBeNull();
    expect(parseRate("7")).toBeNull();
  });
  it("formats durations", () => {
    expect(humanDuration(2700)).toBe("45m");
    expect(humanDuration(112320)).toBe("1d 7h");
    expect(humanDuration(5400)).toBe("1h 30m");
  });
});

describe("MerchantMetricsViz", () => {
  it("draws only fields the contract provides", () => {
    render(<MerchantMetricsViz m={FIXTURE_MERCHANT_METRICS} />);
    expect(screen.getByText("₹1,000.00")).toBeInTheDocument();
    expect(screen.getByText("40.0%")).toBeInTheDocument();
    expect(screen.getByText("3 open")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Top causes" })).toHaveTextContent(
      "duplicate payment",
    );
  });
});
