import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import SignupPage from "@/app/signup/page";
import LegacyRegisterPage from "@/app/customer/register/page";
import AuthWorkspacesPage from "@/app/auth/workspaces/page";
import { getSharedIdentityStub, resetSharedIdentityStub } from "../stubs/identity";
import { resetIdentityClientCache } from "@/lib/server/identity-client";

const state = vi.hoisted(() => ({ session: "" }));
vi.mock("next/navigation", () => ({
  redirect: (url: string) => {
    throw new Error(`REDIRECT:${url}`);
  },
}));
vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => (state.session ? { value: state.session } : undefined) }),
}));
vi.mock("@/lib/server/auth-actions", () => ({
  registerCustomerAction: vi.fn(),
  registerMerchantAction: vi.fn(),
  switchWorkspaceAction: vi.fn(),
}));

describe("signup and own workspace routes", () => {
  it("shows a real-peer multi-workspace chooser for an unscoped cookie without requiring active me", async () => {
    vi.stubEnv("NEXT_PUBLIC_SHELL_MODE", "real-peers");
    vi.stubEnv("IDENTITY_BASE_URL", "http://identity.test");
    const fetchMock = vi.fn(async (url: string) => {
      if (url.endsWith("/v1/auth/me"))
        return Response.json({
          user: {
            user_id: "u",
            email: "dual@example.test",
            account_type: "staff",
            status: "active",
          },
          workspaces: [],
          active_assignment: null,
        });
      return Response.json({
        workspaces: [
          {
            assignment_id: "ops",
            tenant_id: "tenant-demo",
            role_id: "operator",
            scope_key: "tenant-demo",
            status: "active",
          },
          {
            assignment_id: "sup",
            tenant_id: "tenant-demo",
            role_id: "supervisor",
            scope_key: "tenant-demo",
            status: "active",
          },
        ],
        active_assignment: null,
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    state.session = "unscoped-secret";
    try {
      render(await AuthWorkspacesPage());
      expect(screen.getByTestId("select-workspace-ops")).toBeEnabled();
      expect(screen.getByTestId("select-workspace-sup")).toBeEnabled();
      expect(fetchMock).toHaveBeenCalledWith(
        "http://identity.test/v1/auth/workspaces",
        expect.objectContaining({
          headers: expect.objectContaining({ Authorization: "Bearer unscoped-secret" }),
        }),
      );
    } finally {
      state.session = "";
      vi.unstubAllGlobals();
      vi.unstubAllEnvs();
    }
  });

  it("redirects legacy registration to customer signup", () => {
    expect(() => LegacyRegisterPage()).toThrow("REDIRECT:/signup?type=customer");
  });
  it("loads merchant tab and email from query; staff type falls back to customer", async () => {
    const view = render(
      await SignupPage({
        searchParams: Promise.resolve({ type: "merchant", email: "new@example.test" }),
      }),
    );
    expect(screen.getByRole("tab", { name: "Merchant" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText("Email")).toHaveValue("new@example.test");
    view.unmount();
    render(await SignupPage({ searchParams: Promise.resolve({ type: "admin" }) }));
    expect(screen.getByRole("tab", { name: "Customer" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByRole("tab")).toHaveLength(2);
  });
  it("chooser lists only authenticated user's real assignments, including selectable default", async () => {
    process.env.NEXT_PUBLIC_SHELL_MODE = "fixture";
    resetSharedIdentityStub();
    resetIdentityClientCache();
    const logged = getSharedIdentityStub().login("dual@example.test", "demo-dual");
    expect(logged.ok).toBe(true);
    if (!logged.ok) return;
    state.session = logged.session.session_id;
    render(await AuthWorkspacesPage());
    expect(screen.getByTestId("auth-workspaces-list").querySelectorAll("button")).toHaveLength(2);
    expect(screen.queryByText(/Customer|Merchant|Admin/)).not.toBeInTheDocument();
    for (const workspace of logged.workspaces) {
      expect(screen.getByTestId(`select-workspace-${workspace.assignment_id}`)).toBeEnabled();
    }
    state.session = "";
  });
});
