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
  registerMerchantAction: vi.fn(),
  switchWorkspaceAction: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/operator/dashboard",
  useRouter: () => ({ push: () => {} }),
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
    expect(screen.getByTestId("landing-dashboard")).toHaveAttribute("href", "/operator/dashboard");
    expect(screen.queryByRole("link", { name: "Get started" })).not.toBeInTheDocument();
  });

  it("shared login asks only for email and password", () => {
    render(<RoleLogin />);
    expect(screen.getByLabelText("Email")).toHaveAttribute("name", "email");
    expect(screen.getByLabelText("Password")).toHaveAttribute("name", "password");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByText("Choose a portal")).not.toBeInTheDocument();
    expect(screen.getByTestId("register-link")).toHaveAttribute("href", "/signup");
  });

  it("sign-in failure remains visible", async () => {
    const user = userEvent.setup();
    render(<RoleLogin />);
    await user.type(screen.getByTestId("login-email"), "customer@example.test");
    await user.type(screen.getByTestId("login-password"), "demo-customer");
    await user.click(screen.getByTestId("login-submit"));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("invite form has no customer role option (customer cannot staff-register)", () => {
    render(<InviteStaffForm />);
    const select = screen.getByTestId("invite-role");
    const values = Array.from(select.querySelectorAll("option")).map(
      (o) => (o as HTMLOptionElement).value,
    );
    expect(values).not.toContain("customer");
    expect(values).toEqual(["merchant", "operator", "supervisor", "risk", "admin"]);
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
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("aria-current", "page");
  });
});
