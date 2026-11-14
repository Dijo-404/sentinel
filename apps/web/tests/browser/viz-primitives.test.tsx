import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatBlock } from "@/components/viz/stat-block";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { TrendPill } from "@/components/viz/trend-pill";
import { ChartCard } from "@/components/viz/chart-card";
import { fixtureSeries } from "@/components/viz/fixture-series";
import { usdCompact } from "@/components/viz/format";
import { Bars3D } from "@/components/viz/bars-3d";

describe("chart labelling", () => {
  it("dateLabels ends on the fixed simulator day and crosses months", () => {
    expect(fixtureSeries.dateLabels(14)).toEqual([
      "Oct 31",
      "Nov 1",
      "Nov 2",
      "Nov 3",
      "Nov 4",
      "Nov 5",
      "Nov 6",
      "Nov 7",
      "Nov 8",
      "Nov 9",
      "Nov 10",
      "Nov 11",
      "Nov 12",
      "Nov 13",
    ]);
  });

  it("usdCompact shortens money for axes", () => {
    expect(usdCompact(842.4)).toBe("$842");
    expect(usdCompact(8800)).toBe("$8.8k");
    expect(usdCompact(1_250_000)).toBe("$1.3M");
    expect(usdCompact(0)).toBe("$0");
  });

  it("Bars3D without WebGL shows every value and a labelled axis button per bar", () => {
    render(
      <Bars3D
        bars={[
          { label: "Mon", value: 40 },
          { label: "Tue", value: 45 },
        ]}
        unit="cases"
      />,
    );
    expect(screen.getByText("85")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Mon: 40 cases" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Tue: 45 cases" }),
    ).toBeInTheDocument();
  });
});

describe("viz primitives", () => {
  it("renders StatBlock + FixtureBanner with simulator copy", () => {
    render(
      <>
        <FixtureBanner />
        <StatBlock label="Open exceptions" value="12" caption="Last 24h" />
      </>,
    );

    expect(screen.getByTestId("fixture-banner")).toHaveTextContent(
      "Simulator / fixture — not live production metrics",
    );
    expect(screen.getByTestId("stat-block")).toHaveTextContent(
      "Open exceptions",
    );
    expect(screen.getByTestId("stat-block")).toHaveTextContent("12");
    expect(screen.getByTestId("stat-block")).toHaveTextContent("Last 24h");
  });

  it("renders TrendPill and ChartCard", () => {
    render(
      <>
        <TrendPill value="4.2%" direction="up" />
        <ChartCard title="Volume">
          <p>chart</p>
        </ChartCard>
      </>,
    );
    expect(screen.getByTestId("trend-pill")).toHaveAttribute(
      "data-direction",
      "up",
    );
    expect(screen.getByTestId("chart-card")).toHaveTextContent("Volume");
  });

  it("fixtureSeries helpers return synthetic points", () => {
    const daily = fixtureSeries.dailySeries(5, 1, 50);
    expect(daily).toHaveLength(5);
    expect(daily.every((n) => typeof n === "number")).toBe(true);

    const labeled = fixtureSeries.labeledSeries(3);
    expect(labeled).toEqual([
      expect.objectContaining({ x: "D01", y: expect.any(Number) }),
      expect.objectContaining({ x: "D02", y: expect.any(Number) }),
      expect.objectContaining({ x: "D03", y: expect.any(Number) }),
    ]);

    const paired = fixtureSeries.volumeVsRefunds(4);
    expect(paired.volume).toHaveLength(4);
    expect(paired.refundRequests).toHaveLength(4);
  });
});
