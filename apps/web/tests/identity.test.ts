import { beforeEach, describe, expect, it } from "vitest";
import {
  createIdentityStub,
  getSharedIdentityStub,
  resetSharedIdentityStub,
} from "./stubs/identity";
import { getIdentityClient } from "@/lib/server/identity-client";
import {
  isSafeInternalPath,
  portalPath,
  safePortalRedirect,
  workspaceChoices,
} from "@/lib/server/auth";
import { PeerError } from "@/domain/types";

describe("identity stub", () => {
  beforeEach(() => {
    resetSharedIdentityStub();
  });

  it("logs in seeded customer and lists customer workspace only", () => {
    const id = getSharedIdentityStub();
    const result = id.login("customer@example.test", "demo-customer");
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.workspaces.map((w) => w.role)).toEqual(["customer"]);
  });

  it("rejects privileged fields on customer register", () => {
    const id = createIdentityStub();
    const rejected = id.registerCustomer({
      email: "new@example.test",
      display_name: "New Customer",
      password: "password1",
      roles: ["admin"],
    });
    expect(rejected).toEqual({
      ok: false,
      code: "PRIVILEGED_FIELDS_REJECTED",
    });
  });

  it("creates customer without caller-controlled role", () => {
    const id = createIdentityStub();
    const created = id.registerCustomer({
      email: "new@example.test",
      display_name: "New Customer",
      password: "password1",
    });
    expect(created.ok).toBe(true);
    if (!created.ok) return;
    expect(created.user.assignments.every((a) => a.role === "customer")).toBe(
      true,
    );
  });

  it("admin invite rejects customer role (no staff-register path)", () => {
    const id = createIdentityStub();
    const admin = id.login("admin@example.test", "demo-admin");
    expect(admin.ok).toBe(true);
    if (!admin.ok) return;
    const invite = id.inviteStaff(admin.user.user_id, {
      display_name: "Nope",
      work_email: "nope@example.test",
      tenant_id: "tenant-demo",
      role_id: "customer",
    });
    expect(invite.ok).toBe(false);
    if (invite.ok) return;
    expect(invite.code).toBe("INVALID_ROLE");
  });

  it("assignable roles never include customer", () => {
    const roles = createIdentityStub().assignableRoles().map((r) => r.role_id);
    expect(roles).not.toContain("customer");
  });
});

describe("auth helpers", () => {
  it("portalPath builds role dashboards", () => {
    expect(portalPath("operator")).toBe("/operator/dashboard");
  });

  it("isSafeInternalPath rejects open redirects and traversal", () => {
    expect(isSafeInternalPath("/customer/dashboard", "customer")).toBe(true);
    expect(isSafeInternalPath("//evil.example", "customer")).toBe(false);
    expect(isSafeInternalPath("https://evil.example", "customer")).toBe(false);
    expect(isSafeInternalPath("/customer/../admin", "customer")).toBe(false);
    expect(isSafeInternalPath(null)).toBe(false);
    expect(safePortalRedirect("/admin/users", "admin")).toBe("/admin/users");
    expect(safePortalRedirect("/ops", "admin")).toBe("/admin/dashboard");
  });

  it("selectAssignment binds matching portal role", () => {
    const id = createIdentityStub();
    // Seed a multi-role user by inviting is N/A; mutate via login + select on admin.
    const login = id.login("admin@example.test", "demo-admin");
    expect(login.ok).toBe(true);
    if (!login.ok) return;
    const asg = login.workspaces[0]!;
    const selected = id.selectAssignment(login.session.session_id, asg.assignment_id);
    expect(selected?.active_assignment_id).toBe(asg.assignment_id);
  });

  it("workspaceChoices maps authorized portals only", () => {
    const choices = workspaceChoices([
      {
        assignment_id: "a1",
        role: "operator",
        tenant_id: "tenant-demo",
        label: "Ops",
      },
    ]);
    expect(choices).toEqual([
      {
        role: "operator",
        href: "/operator/dashboard",
        label: "Support Operator — Ops",
      },
    ]);
  });

  it("real-peers identity refuses NEXT_PUBLIC demo token alone", () => {
    expect(() =>
      getIdentityClient({
        NEXT_PUBLIC_SHELL_MODE: "real-peers",
        NEXT_PUBLIC_DEMO_TOKEN: "tok-public",
      }),
    ).toThrow(PeerError);
  });

  it("fixture identity returns shared stub", () => {
    const a = getIdentityClient({ NEXT_PUBLIC_SHELL_MODE: "fixture" });
    const b = getIdentityClient({ NEXT_PUBLIC_SHELL_MODE: "fixture" });
    expect(a).toBe(b);
  });
});
