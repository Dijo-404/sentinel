import { beforeAll, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { caseHref, navShortcuts } from "@/components/shell/command-palette";
import { PortalTopbar } from "@/components/shell/portal-topbar";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/operator/dashboard",
}));

beforeAll(() => {
  // cmdk measures items via ResizeObserver and scrollIntoView, which jsdom lacks.
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
  Element.prototype.scrollIntoView ??= () => {};
});

const nav = [
  { href: "/operator/dashboard", label: "Dashboard" },
  { href: "/operator/queue", label: "Queue" },
  { href: "/supervisor/approvals", label: "Approvals" },
  { href: "/supervisor/audit", label: "Audit" },
];

describe("shell helpers", () => {
  it("assigns a unique G-shortcut letter per nav item", () => {
    const m = navShortcuts(nav);
    expect(m.get("d")?.label).toBe("Dashboard");
    expect(m.get("a")?.label).toBe("Approvals");
    expect(m.get("u")?.label).toBe("Audit");
  });

  it("routes typed case references per portal", () => {
    expect(caseHref("operator", "case_91A")).toBe("/operator/cases/case_91A");
    expect(caseHref("customer", "case_91A")).toBe("/cases/case_91A");
  });
});

describe("PortalTopbar", () => {
  it("shows the configured mode verbatim", () => {
    render(<PortalTopbar portal="operator" nav={nav} mode="fixture data" />);
    expect(screen.getByText("fixture data")).toBeInTheDocument();
  });

  it("opens the palette with ⌘K and filters nav", () => {
    render(<PortalTopbar portal="operator" nav={nav} mode="fixture data" />);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const input = screen.getByPlaceholderText(/Type a page, action or case reference/);
    fireEvent.change(input, { target: { value: "queue" } });
    expect(screen.getByRole("option", { name: /Queue/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Audit/ })).not.toBeInTheDocument();
  });

  it("G then Q navigates, ? opens the shortcut sheet", () => {
    push.mockClear();
    render(<PortalTopbar portal="operator" nav={nav} mode="fixture data" />);
    fireEvent.keyDown(window, { key: "g" });
    fireEvent.keyDown(window, { key: "q" });
    expect(push).toHaveBeenCalledWith("/operator/queue");
    fireEvent.keyDown(window, { key: "?" });
    expect(screen.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeInTheDocument();
  });
});
