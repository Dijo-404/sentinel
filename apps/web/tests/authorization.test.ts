import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ingressHeaders = new Headers();

const cookieStore = {
  value: undefined as string | undefined,
  set: vi.fn((name: string, value: string, _options?: { maxAge?: number }) => {
    if (name === "sentinel_session") cookieStore.value = value;
  }),
  delete: vi.fn((name: string) => {
    if (name === "sentinel_session") cookieStore.value = undefined;
  }),
  get: vi.fn((name: string) => {
    if (name === "sentinel_session" && cookieStore.value) {
      return { value: cookieStore.value };
    }
    return undefined;
  }),
};

vi.mock("next/headers", () => ({
  cookies: async () => cookieStore,
  headers: async () => ingressHeaders,
}));

const redirectMock = vi.fn((url: string) => {
  throw new Error(`REDIRECT:${url}`);
});

vi.mock("next/navigation", () => ({
  redirect: (url: string) => redirectMock(url),
}));

import { resetSharedIdentityStub } from "./stubs/identity";
import { resetIdentityClientCache } from "@/lib/server/identity-client";
import {
  loginWithCredentials,
  setSessionCookie,
  registerCustomerAccount,
  safePortalRedirect,
  isSafeInternalPath,
  switchActiveAssignment,
} from "@/lib/server/auth";
import { requireRole } from "@/lib/server/authorization";

// Auth helpers read process.env via getIdentityClient(); product default is real-peers.
beforeEach(() => {
  process.env.NEXT_PUBLIC_SHELL_MODE = "fixture";
});

describe("login session cookie policy", () => {
  beforeEach(() => {
    resetSharedIdentityStub();
    resetIdentityClientCache();
    cookieStore.value = undefined;
    cookieStore.set.mockClear();
    cookieStore.delete.mockClear();
    redirectMock.mockClear();
  });

  afterEach(() => vi.unstubAllEnvs());

  it.each([
    [undefined, undefined, true],
    ["1", undefined, true],
    [undefined, "1", true],
    ["1", "1", false],
  ])(
    "keeps production cookies secure unless both HTTP sandbox flags are enabled (%s, %s)",
    async (sandbox, http, secure) => {
      vi.stubEnv("NODE_ENV", "production");
      vi.stubEnv("SENTINEL_V1_SANDBOX", sandbox);
      vi.stubEnv("WEB_ALLOW_HTTP_SANDBOX", http);
      await setSessionCookie("synthetic-session");
      expect(cookieStore.set).toHaveBeenCalledWith(
        "sentinel_session",
        "synthetic-session",
        expect.objectContaining({ secure, httpOnly: true, sameSite: "lax", path: "/" }),
      );
    },
  );

  it("sets cookie after selecting the account workspace", async () => {
    const result = await loginWithCredentials("operator@example.test", "demo-operator");
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.session.assignment.role).toBe("operator");
    expect(cookieStore.set).toHaveBeenCalled();
    expect(cookieStore.value).toBe(result.session.session.session_id);
    expect(result.session.session.active_assignment_id).toBe(
      result.session.assignment.assignment_id,
    );
  });

  it("chooses the account's single workspace without accepting a role", async () => {
    const result = await loginWithCredentials("customer@example.test", "demo-customer");
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.redirectTo).toBe("/customer/dashboard");
    expect(cookieStore.value).toBe(result.session.session.session_id);
  });

  it("keeps multi-workspace session for the chooser", async () => {
    const result = await loginWithCredentials("dual@example.test", "demo-dual");
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.redirectTo).toBe("/auth/workspaces");
    expect(result.session.workspaces.map((w) => w.role)).toEqual(["operator", "supervisor"]);
    expect(cookieStore.set).toHaveBeenCalledWith(
      "sentinel_session",
      expect.any(String),
      expect.objectContaining({ httpOnly: true, sameSite: "lax", path: "/" }),
    );
  });

  it("redirects unknown email to signup with encoded prefill", async () => {
    const { loginAction } = await import("@/lib/server/auth-actions");
    const data = new FormData();
    data.set("email", "new+person@example.test");
    data.set("password", "password1");
    await expect(loginAction(null, data)).rejects.toThrow(
      "REDIRECT:/signup?email=new%2Bperson%40example.test",
    );
    expect(cookieStore.value).toBeUndefined();
  });

  it("keeps wrong password generic and never redirects to signup", async () => {
    const { loginAction } = await import("@/lib/server/auth-actions");
    const data = new FormData();
    data.set("email", "customer@example.test");
    data.set("password", "wrong");
    expect(await loginAction(null, data)).toMatchObject({
      ok: false,
      message: "Sign-in failed. Check your credentials and try again.",
    });
    expect(redirectMock).not.toHaveBeenCalled();
  });

  it("ignores supplied portal and unsafe next while redirecting to the account dashboard", async () => {
    const { loginAction } = await import("@/lib/server/auth-actions");
    const data = new FormData();
    data.set("email", "customer@example.test");
    data.set("password", "demo-customer");
    data.set("role", "admin");
    data.set("next", "/admin/users");
    await expect(loginAction(null, data)).rejects.toThrow("REDIRECT:/customer/dashboard");
  });

  it("passes authenticated ingress IP to identity and ignores spoofed forwarded headers", async () => {
    const { loginAction } = await import("@/lib/server/auth-actions");
    const { getIdentityClient } = await import("@/lib/server/identity-client");
    const login = vi.spyOn(getIdentityClient(), "login");
    const data = new FormData();
    data.set("email", "customer@example.test");
    data.set("password", "demo-customer");
    const token = "c".repeat(32);
    vi.stubEnv("WEB_TRUSTED_INGRESS_TOKEN", token);
    ingressHeaders.set("x-forwarded-for", "198.51.100.99");
    ingressHeaders.set("x-sentinel-client-ip", "198.51.100.8");
    try {
      await expect(loginAction(null, data)).rejects.toThrow("REDIRECT:/customer/dashboard");
      expect(login).toHaveBeenLastCalledWith("customer@example.test", "demo-customer", undefined);
      ingressHeaders.set("x-sentinel-ingress-token", token);
      await expect(loginAction(null, data)).rejects.toThrow("REDIRECT:/customer/dashboard");
      expect(login).toHaveBeenLastCalledWith(
        "customer@example.test",
        "demo-customer",
        "198.51.100.8",
      );
    } finally {
      vi.unstubAllEnvs();
      ingressHeaders.forEach((_value, key) => ingressHeaders.delete(key));
      login.mockRestore();
    }
  });

  it("fails closed and revokes provisional session when workspaces unavailable", async () => {
    const { getIdentityClient } = await import("@/lib/server/identity-client");
    const identity = getIdentityClient();
    vi.spyOn(identity, "listWorkspaces").mockRejectedValueOnce(new Error("peer down"));
    const logout = vi.spyOn(identity, "logout");
    const result = await loginWithCredentials("customer@example.test", "demo-customer");
    expect(result.ok).toBe(false);
    expect(cookieStore.value).toBeUndefined();
    expect(logout).toHaveBeenCalled();
    vi.restoreAllMocks();
  });
});

describe("registerCustomerAccount privileged strip", () => {
  beforeEach(() => {
    resetSharedIdentityStub();
    cookieStore.value = undefined;
  });

  it("rejects roles/tenant_id/subject_refs before peer call", async () => {
    const rejected = await registerCustomerAccount({
      email: "x@example.test",
      display_name: "X",
      password: "password1",
      roles: ["admin"],
    });
    expect(rejected).toEqual({
      ok: false,
      code: "PRIVILEGED_FIELDS_REJECTED",
      message: "Registration rejected privileged fields",
    });
  });
});

describe("safePortalRedirect", () => {
  it("normalizes and enforces exact portal prefix", () => {
    expect(safePortalRedirect("/operator/dashboard", "operator")).toBe("/operator/dashboard");
    expect(safePortalRedirect("/operator", "operator")).toBe("/operator");
    expect(safePortalRedirect("/operator/../admin", "operator")).toBe("/operator/dashboard");
    expect(safePortalRedirect("//evil", "operator")).toBe("/operator/dashboard");
    expect(safePortalRedirect("/customer/dashboard", "operator")).toBe("/operator/dashboard");
    expect(isSafeInternalPath("/operator/%2e%2e/admin", "operator")).toBe(false);
  });
});

describe("requireRole unauthenticated redirect", () => {
  beforeEach(() => {
    resetSharedIdentityStub();
    cookieStore.value = undefined;
    redirectMock.mockClear();
  });

  it("redirects unauthenticated access to role login", async () => {
    await expect(requireRole("admin")).rejects.toThrow("REDIRECT:/login?portal=admin");
    expect(redirectMock).toHaveBeenCalledWith("/login?portal=admin");
  });
});

describe("requireRole active assignment only", () => {
  beforeEach(() => {
    resetSharedIdentityStub();
    resetIdentityClientCache();
    cookieStore.value = undefined;
    cookieStore.set.mockClear();
    cookieStore.delete.mockClear();
    redirectMock.mockClear();
  });

  it("rejects dual-role user when active assignment mismatches portal", async () => {
    const login = await loginWithCredentials("dual@example.test", "demo-dual");
    expect(login.ok).toBe(true);
    if (!login.ok) return;
    expect(login.session.assignment.role).toBe("operator");
    expect(cookieStore.value).toBe(login.session.session.session_id);

    await expect(requireRole("supervisor")).rejects.toThrow(
      "REDIRECT:/unauthorized?portal=supervisor",
    );
  });

  it("switches dual-role workspace in-session without logout", async () => {
    const login = await loginWithCredentials("dual@example.test", "demo-dual");
    expect(login.ok).toBe(true);
    if (!login.ok) return;
    const supervisorAsg = login.session.workspaces.find((w) => w.role === "supervisor");
    expect(supervisorAsg).toBeDefined();

    const switched = await switchActiveAssignment(supervisorAsg!.assignment_id);
    expect(switched).toEqual({
      ok: true,
      role: "supervisor",
      redirectTo: "/supervisor/dashboard",
    });
    expect(cookieStore.value).toBeTruthy();

    const session = await requireRole("supervisor");
    expect(session.assignment.role).toBe("supervisor");
    expect(session.assignment.assignment_id).toBe(supervisorAsg!.assignment_id);
  });

  it("does not set cookie when selectAssignment fails", async () => {
    const { getIdentityClient } = await import("@/lib/server/identity-client");
    const identity = getIdentityClient();
    const select = vi.spyOn(identity, "selectAssignment").mockResolvedValue(null);

    const result = await loginWithCredentials("operator@example.test", "demo-operator");
    expect(result.ok).toBe(false);
    expect(cookieStore.value).toBeUndefined();
    expect(cookieStore.set).not.toHaveBeenCalled();
    select.mockRestore();
  });

  it("sets cookie maxAge from session expires_at", async () => {
    const result = await loginWithCredentials("operator@example.test", "demo-operator");
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(cookieStore.set).toHaveBeenCalled();
    const call = cookieStore.set.mock.calls.find((c) => c[0] === "sentinel_session");
    expect(call?.[2]?.maxAge).toBeGreaterThan(0);
    expect(call?.[2]?.maxAge).toBeLessThanOrEqual(12 * 60 * 60);
  });
});

describe("public registration actions", () => {
  beforeEach(() => {
    resetSharedIdentityStub();
    resetIdentityClientCache();
    cookieStore.value = undefined;
  });
  it.each(["customer", "merchant"] as const)(
    "registers %s and redirects to its portal",
    async (type) => {
      const { registerCustomerAction, registerMerchantAction } =
        await import("@/lib/server/auth-actions");
      const data = new FormData();
      data.set("email", "new@example.test");
      data.set("display_name", "New User");
      data.set("password", "password1");
      data.set("business_name", "Shop");
      await expect(
        (type === "merchant" ? registerMerchantAction : registerCustomerAction)(null, data),
      ).rejects.toThrow(`REDIRECT:/${type}/dashboard`);
      expect(cookieStore.value).toBeTruthy();
    },
  );
  it.each([
    "roles",
    "role_id",
    "tenant_id",
    "subject_ref",
    "subject_refs",
    "merchant_ref",
    "account_type",
  ])("rejects privileged %s before registration", async (key) => {
    const { registerMerchantAction } = await import("@/lib/server/auth-actions");
    const data = new FormData();
    data.set(key, "admin");
    expect(await registerMerchantAction(null, data)).toEqual({
      ok: false,
      message: "Registration rejected privileged fields",
    });
    expect(cookieStore.value).toBeUndefined();
  });
});

describe("unscoped real-peer workspace selection", () => {
  it("keeps portals closed until selecting an owned workspace from the cookie credential", async () => {
    vi.stubEnv("NEXT_PUBLIC_SHELL_MODE", "real-peers");
    vi.stubEnv("IDENTITY_BASE_URL", "http://identity.test");
    const workspaces = ["operator", "supervisor"].map((role) => ({
      assignment_id: role,
      tenant_id: "tenant-demo",
      role_id: role,
      status: "active",
      scope_key: "tenant-demo",
    }));
    const user = {
      user_id: "dual",
      email: "dual@example.test",
      account_type: "staff",
      status: "active",
    };
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/v1/auth/login"))
        return Response.json({
          user,
          workspaces,
          active_assignment: null,
          session_token: "unscoped",
          expires_at: "2099-01-01T00:00:00Z",
        });
      if (url.endsWith("/v1/auth/me"))
        return Response.json({ user, workspaces, active_assignment: null });
      if (url.endsWith("/v1/auth/workspaces/select"))
        return Response.json({
          session_token: "scoped",
          expires_at: "2099-01-01T00:00:00Z",
          active_assignment: workspaces[1],
        });
      return Response.json({ workspaces, active_assignment: null });
    });
    vi.stubGlobal("fetch", fetchMock);
    try {
      const login = await loginWithCredentials(user.email, "password1");
      expect(login).toMatchObject({ ok: true, redirectTo: "/auth/workspaces" });
      const { getAuthSession } = await import("@/lib/server/auth");
      expect(await getAuthSession()).toBeNull();
      expect(await switchActiveAssignment("supervisor")).toEqual({
        ok: true,
        role: "supervisor",
        redirectTo: "/supervisor/dashboard",
      });
      expect(cookieStore.value).toBe("scoped");
      expect(fetchMock).toHaveBeenCalledWith(
        "http://identity.test/v1/auth/workspaces/select",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ assignment_id: "supervisor" }),
          headers: expect.objectContaining({ Authorization: "Bearer unscoped" }),
        }),
      );
    } finally {
      cookieStore.value = undefined;
      vi.unstubAllGlobals();
      vi.unstubAllEnvs();
    }
  });
});
