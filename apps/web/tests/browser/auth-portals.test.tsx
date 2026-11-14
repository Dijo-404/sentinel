import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RoleLogin } from "@/components/auth/role-login";
import { InviteStaffForm } from "@/components/identity/invite-staff-form";

vi.mock("@/lib/server/auth-actions", () => ({
  loginAction: vi.fn(async () => ({
    ok: false,
    message: "This account does not have the operator workspace.",
    workspaces: [
      { label: "Customer workspace", href: "/customer/dashboard" },
    ],
  })),
  inviteStaffAction: vi.fn(async () => ({
    ok: false,
    message: "Customer role cannot be invited via staff invitation",
  })),
  logoutAction: vi.fn(),
  registerCustomerAction: vi.fn(),
}));

describe("portal auth UI", () => {
  it("customer login shows register link; staff login does not", () => {
    const { unmount } = render(<RoleLogin role="customer" />);
    expect(screen.getByTestId("register-link")).toBeInTheDocument();
    unmount();

    render(<RoleLogin role="operator" />);
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
});
