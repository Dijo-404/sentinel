import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LandingPage } from "@/components/marketing/landing-page";
import { RoleLogin } from "@/components/auth/role-login";
import { InviteStaffForm } from "@/components/identity/invite-staff-form";
import { ProtectedShell } from "@/components/layout/protected-shell";
import type { AuthSession } from "@/lib/server/auth";

vi.mock("@/lib/server/auth-actions", () => ({
  loginAction: vi.fn(async () => ({
    ok: false,
    message: "This account does not have the operator workspace.",
    workspaces: [{ label: "Customer workspace", href: "/customer/dashboard" }],
  })),
  inviteStaffAction: vi.fn(async () => ({
    ok: false,
    message: "Customer role cannot be invited via staff invitation",
  })),
  logoutAction: vi.fn(),
  registerCustomerAction: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/operator/dashboard",
}));

const sessionStub = {
  session: {
    session_id: "s1",
    user_id: "u1",
    active_assignment_id: "a1",
    issued_at: "2026-01-01T00:00:00Z",
    expires_at: "2026-01-02T00:00:00Z",
    revoked: false,
  },
  user: {
    user_id: "u1",
    email: "operator@example.test",
    display_name: "Demo Operator",
    password: "x",
    account_status: "ACTIVE" as const,
    account_class: "staff" as const,
    assignments: [],
  },
  assignment: {
    assignment_id: "a1",
    role: "operator" as const,
    tenant_id: "t1",
    label: "Payments support",
  },
  workspaces: [],
} satisfies AuthSession;

describe("portal auth UI", () => {
  it("landing shows Get started linking to /login", () => {
    render(<LandingPage />);
    expect(screen.getByTestId("landing-page")).toBeInTheDocument();
    const ctas = screen.getAllByRole("link", { name: "Get started" });
    expect(ctas.length).toBeGreaterThan(0);
    expect(ctas[0]).toHaveAttribute("href", "/login");
  });

  it("signed-in landing shows Dashboard instead of Log in", () => {
    render(<LandingPage dashboardHref="/operator/dashboard" />);
    expect(screen.getByTestId("landing-dashboard")).toHaveAttribute(
      "href",
      "/operator/dashboard",
    );
    expect(
      screen.queryByRole("link", { name: "Get started" }),
    ).not.toBeInTheDocument();
  });

  it("shared login has workspace select and role-login testid", () => {
    render(<RoleLogin role="merchant" />);
    expect(screen.getByTestId("role-login")).toBeInTheDocument();
    const select = screen.getByTestId("login-workspace");
    expect(select).toHaveAttribute("name", "role");
    expect(select).toBeRequired();
    const values = Array.from(select.querySelectorAll("option")).map(
      (o) => (o as HTMLOptionElement).value,
    );
    expect(values).toEqual([
      "customer",
      "merchant",
      "operator",
      "supervisor",
      "risk",
      "admin",
    ]);
    expect(select).toHaveValue("merchant");
    expect(screen.getByTestId("demo-users")).toBeInTheDocument();
  });

  it("customer login shows register link; staff login does not", async () => {
    const user = userEvent.setup();
    render(<RoleLogin role="customer" />);
    expect(screen.getByTestId("register-link")).toBeInTheDocument();

    await user.selectOptions(screen.getByTestId("login-workspace"), "operator");
    expect(screen.queryByTestId("register-link")).not.toBeInTheDocument();
    expect(screen.getByTestId("no-signup")).toHaveTextContent(
      "invitation-only",
    );
  });

  it("role mismatch surfaces only authorized workspaces", async () => {
    const user = userEvent.setup();
    render(<RoleLogin role="operator" />);
    await user.type(screen.getByTestId("login-email"), "customer@example.test");
    await user.type(screen.getByTestId("login-password"), "demo-customer");
    await user.click(screen.getByTestId("login-submit"));

    expect(await screen.findByTestId("login-error")).toHaveTextContent(
      "does not have the operator workspace",
    );
    const links = screen.getByTestId("authorized-workspaces");
    expect(links).toHaveTextContent("Customer workspace");
    expect(links).not.toHaveTextContent("admin");
  });

  it("invite form has no customer role option (customer cannot staff-register)", () => {
    render(<InviteStaffForm />);
    const select = screen.getByTestId("invite-role");
    const values = Array.from(select.querySelectorAll("option")).map(
      (o) => (o as HTMLOptionElement).value,
    );
    expect(values).not.toContain("customer");
    expect(values).toEqual([
      "merchant",
      "operator",
      "supervisor",
      "risk",
      "admin",
    ]);
  });

  it("protected shell renders night sidebar with logout and data-portal", () => {
    render(
      <ProtectedShell
        role="operator"
        session={sessionStub}
        nav={[
          { href: "/operator/dashboard", label: "Dashboard" },
          { href: "/operator/queue", label: "Queue" },
        ]}
      >
        <p>content</p>
      </ProtectedShell>,
    );
    const shell = document.querySelector("[data-portal='operator']");
    expect(shell).toBeTruthy();
    expect(screen.getByTestId("logout")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
