import { beforeEach, describe, expect, it, vi } from "vitest";

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
  registerCustomerAccount,
  safePortalRedirect,
  isSafeInternalPath,
  switchActiveAssignment,
} from "@/lib/server/auth";
import { requireRole } from "@/lib/server/authorization";

describe("login session cookie policy", () => {
  beforeEach(() => {
    resetSharedIdentityStub();
    resetIdentityClientCache();
    cookieStore.value = undefined;
    cookieStore.set.mockClear();
    cookieStore.delete.mockClear();
    redirectMock.mockClear();
  });

  it("sets cookie only after role match and activates matching assignment", async () => {
    const result = await loginWithCredentials(
      "operator@example.test",
      "demo-operator",
      "operator",
    );
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.role_match).toBe(true);
    expect(result.session.assignment.role).toBe("operator");
    expect(cookieStore.set).toHaveBeenCalled();
    expect(cookieStore.value).toBe(result.session.session.session_id);
    expect(result.session.session.active_assignment_id).toBe(
      result.session.assignment.assignment_id,
    );
  });

  it("clears cookie and does not keep session on role mismatch", async () => {
    const result = await loginWithCredentials(
      "customer@example.test",
      "demo-customer",
      "operator",
    );
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.role_match).toBe(false);
    expect(cookieStore.value).toBeUndefined();
    expect(cookieStore.delete).toHaveBeenCalled();
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
    expect(safePortalRedirect("/operator/dashboard", "operator")).toBe(
      "/operator/dashboard",
    );
    expect(safePortalRedirect("/operator", "operator")).toBe("/operator");
    expect(safePortalRedirect("/operator/../admin", "operator")).toBe(
      "/operator/dashboard",
    );
    expect(safePortalRedirect("//evil", "operator")).toBe(
      "/operator/dashboard",
    );
    expect(safePortalRedirect("/customer/dashboard", "operator")).toBe(
      "/operator/dashboard",
    );
    expect(isSafeInternalPath("/operator/%2e%2e/admin", "operator")).toBe(
      false,
    );
  });
});

describe("requireRole unauthenticated redirect", () => {
  beforeEach(() => {
    resetSharedIdentityStub();
    cookieStore.value = undefined;
    redirectMock.mockClear();
  });

  it("redirects unauthenticated access to role login", async () => {
    await expect(requireRole("admin")).rejects.toThrow(
      "REDIRECT:/login?portal=admin",
    );
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
    const login = await loginWithCredentials(
      "dual@example.test",
      "demo-dual",
      "operator",
    );
    expect(login.ok).toBe(true);
    if (!login.ok) return;
    expect(login.role_match).toBe(true);
    expect(login.session.assignment.role).toBe("operator");
    expect(cookieStore.value).toBe(login.session.session.session_id);

    await expect(requireRole("supervisor")).rejects.toThrow(
      "REDIRECT:/unauthorized?portal=supervisor",
    );
  });

  it("switches dual-role workspace in-session without logout", async () => {
    const login = await loginWithCredentials(
      "dual@example.test",
      "demo-dual",
      "operator",
    );
    expect(login.ok).toBe(true);
    if (!login.ok) return;
    const supervisorAsg = login.session.workspaces.find(
      (w) => w.role === "supervisor",
    );
    expect(supervisorAsg).toBeDefined();

    const switched = await switchActiveAssignment(
      supervisorAsg!.assignment_id,
    );
    expect(switched).toEqual({
      ok: true,
      role: "supervisor",
      redirectTo: "/supervisor/dashboard",
    });
    expect(cookieStore.value).toBeTruthy();

    const session = await requireRole("supervisor");
    expect(session.assignment.role).toBe("supervisor");
    expect(session.assignment.assignment_id).toBe(
      supervisorAsg!.assignment_id,
    );
  });

  it("does not set cookie when selectAssignment fails", async () => {
    const { getIdentityClient } = await import("@/lib/server/identity-client");
    const identity = getIdentityClient();
    const select = vi
      .spyOn(identity, "selectAssignment")
      .mockResolvedValue(null);

    const result = await loginWithCredentials(
      "operator@example.test",
      "demo-operator",
      "operator",
    );
    expect(result.ok).toBe(false);
    expect(cookieStore.value).toBeUndefined();
    expect(cookieStore.set).not.toHaveBeenCalled();
    select.mockRestore();
  });

  it("sets cookie maxAge from session expires_at", async () => {
    const result = await loginWithCredentials(
      "operator@example.test",
      "demo-operator",
      "operator",
    );
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(cookieStore.set).toHaveBeenCalled();
    const call = cookieStore.set.mock.calls.find(
      (c) => c[0] === "sentinel_session",
    );
    expect(call?.[2]?.maxAge).toBeGreaterThan(0);
    expect(call?.[2]?.maxAge).toBeLessThanOrEqual(12 * 60 * 60);
  });
});
