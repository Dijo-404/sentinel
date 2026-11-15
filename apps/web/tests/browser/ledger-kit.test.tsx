import { afterEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { formatMoney } from "@/components/ledger/money";
import { layoutSankey } from "@/components/ledger/sankey";
import { computeWaterfall } from "@/components/ledger/waterfall";
import { neighbours } from "@/components/ledger/link-graph";
import { linePath, stackPaths } from "@/components/ledger/charts";
import { HoldButton } from "@/components/ledger/hold-button";
import { NumberRoll } from "@/components/ledger/number-roll";
import { StackedBars } from "@/components/ledger/stacked-bars";

describe("formatMoney", () => {
  it("formats integer minor units with explicit currency", () => {
    expect(formatMoney(4250, "USD")).toBe("$42.50");
    expect(formatMoney(12845000, "INR")).toBe("₹1,28,450.00");
    expect(formatMoney(500, "JPY")).toBe("¥500");
  });
});

describe("layoutSankey", () => {
  const nodes = [
    { id: "a", label: "A", column: 0, color: "x" },
    { id: "b", label: "B", column: 0, color: "x" },
    { id: "c", label: "C", column: 1, color: "x" },
  ];
  const links = [
    { source: "a", target: "c", value: 30, color: "x" },
    { source: "b", target: "c", value: 10, color: "x" },
  ];
  it("sizes nodes by flow and stacks ribbons without overlap", () => {
    const { nodes: n, links: l } = layoutSankey(nodes, links, { width: 100, height: 100, gap: 0 });
    const c = n.find((x) => x.id === "c")!;
    expect(c.value).toBe(40);
    expect(c.h).toBeCloseTo(100);
    expect(l[0].width).toBeCloseTo(75);
    expect(l[1].width).toBeCloseTo(25);
    expect(n.find((x) => x.id === "b")!.y).toBeCloseTo(75);
  });
});

describe("computeWaterfall", () => {
  it("floats deltas from the running balance and ends at the net", () => {
    const { geo, end } = computeWaterfall([
      { label: "Gross", value: 100, kind: "total", color: "x" },
      { label: "Fees", value: -10, kind: "delta", color: "x" },
      { label: "Refunds", value: -20, kind: "delta", color: "x" },
    ]);
    expect(end).toBe(70);
    expect(geo[1]).toMatchObject({ base: 90, size: 10 });
    expect(geo[2]).toMatchObject({ base: 70, size: 20 });
  });
});

describe("chart paths", () => {
  it("linePath scales to the box", () => {
    expect(linePath([0, 10], 100, 50, 10)).toBe("M0.0 50.0 L100.0 0.0");
  });
  it("stackPaths returns one closed path per layer", () => {
    const p = stackPaths([[1, 1], [2, 2]], 10, 10);
    expect(p).toHaveLength(2);
    expect(p.every((d) => d.endsWith("Z"))).toBe(true);
  });
  it("neighbours includes the node and its direct links", () => {
    const n = neighbours("a", [{ a: "a", b: "b", type: "device" }, { a: "c", b: "d", type: "route" }]);
    expect([...n].sort()).toEqual(["a", "b"]);
  });
});

describe("HoldButton", () => {
  afterEach(() => vi.useRealTimers());

  it("commits only after the full hold and cancels on early release", () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "requestAnimationFrame", "cancelAnimationFrame", "performance"] });
    const onCommit = vi.fn();
    render(<HoldButton label="Hold to approve" durationMs={600} onCommit={onCommit} />);
    const btn = screen.getByRole("button", { name: "Hold to approve" });

    fireEvent.pointerDown(btn);
    act(() => vi.advanceTimersByTime(250));
    fireEvent.pointerUp(btn);
    act(() => vi.advanceTimersByTime(800));
    expect(onCommit).not.toHaveBeenCalled();
    expect(btn).toHaveTextContent("Hold to approve");

    fireEvent.keyDown(btn, { key: " " });
    act(() => vi.advanceTimersByTime(800));
    expect(onCommit).toHaveBeenCalledTimes(1);
  });
});

describe("NumberRoll", () => {
  it("exposes the plain value to assistive tech", () => {
    render(<NumberRoll value="₹1,284" />);
    expect(screen.getByText("₹1,284")).toHaveClass("sr-only");
  });
});

describe("StackedBars", () => {
  it("offers a data-table fallback and legend toggles", () => {
    render(
      <StackedBars
        caption="Refunds by reason"
        series={[{ key: "a", label: "Not received", color: "red" }]}
        rows={[{ label: "Nov 1", values: { a: 4 } }]}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Show as table" }));
    expect(screen.getByRole("table")).toHaveTextContent("Not received");
    const legend = screen.getByRole("button", { name: "Not received" });
    fireEvent.click(legend);
    expect(legend).toHaveAttribute("aria-pressed", "false");
  });
});
