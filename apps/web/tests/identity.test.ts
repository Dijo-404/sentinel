import { beforeEach, describe, expect, it } from "vitest";
import {
  createIdentityStub,
  getSharedIdentityStub,
  resetSharedIdentityStub,
} from "./stubs/identity";
import {
  getIdentityClient,
  resetIdentityClientCache,
} from "@/lib/server/identity-client";
import { createRealPeerIdentityClient } from "@/adapters/real-peer-identity-client";
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
    resetIdentityClientCache();
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

  it("invite rejects ACTIVE user email as DUPLICATE", () => {
    const id = createIdentityStub();
    const admin = id.login("admin@example.test", "demo-admin");
    expect(admin.ok).toBe(true);
    if (!admin.ok) return;
    const invite = id.inviteStaff(admin.user.user_id, {
      display_name: "Dup Operator",
      work_email: "operator@example.test",
      tenant_id: "tenant-demo",
      role_id: "operator",
    });
    expect(invite.ok).toBe(false);
    if (invite.ok) return;
    expect(invite.code).toBe("DUPLICATE");
  });

  it("assignable roles never include customer", () => {
    const roles = createIdentityStub()
      .assignableRoles()
      .map((r) => r.role_id);
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
    const selected = id.selectAssignment(
      login.session.session_id,
      asg.assignment_id,
    );
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
        assignment_id: "a1",
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

  it("real-peers refuses missing IDENTITY_BASE_URL", () => {
    expect(() =>
      getIdentityClient({
        NEXT_PUBLIC_SHELL_MODE: "real-peers",
      }),
    ).toThrow(PeerError);
    try {
      getIdentityClient({ NEXT_PUBLIC_SHELL_MODE: "real-peers" });
    } catch (err) {
      expect(err).toBeInstanceOf(PeerError);
      expect((err as PeerError).message).toMatch(/IDENTITY_BASE_URL/);
    }
  });

  it("real-peers refuses NEXT_PUBLIC identity secrets", () => {
    expect(() =>
      getIdentityClient({
        NEXT_PUBLIC_SHELL_MODE: "real-peers",
        IDENTITY_BASE_URL: "http://127.0.0.1:8012",
        NEXT_PUBLIC_IDENTITY_PASSWORD: "secret",
      }),
    ).toThrow(PeerError);
  });

  it("fixture identity returns shared client", () => {
    const a = getIdentityClient({ NEXT_PUBLIC_SHELL_MODE: "fixture" });
    const b = getIdentityClient({ NEXT_PUBLIC_SHELL_MODE: "fixture" });
    expect(a).toBe(b);
  });
});

describe("real-peer identity client", () => {
  it("surfaces network failure without fixture fallback", async () => {
    const client = createRealPeerIdentityClient({
      baseUrl: "http://127.0.0.1:8012",
      fetchImpl: async () => {
        throw new Error("peer down");
      },
    });
    await expect(client.login("a@b.test", "x")).rejects.toMatchObject({
      code: "PEER_UNAVAILABLE",
    });
  });

  it("rejects malformed JSON body", async () => {
    const client = createRealPeerIdentityClient({
      baseUrl: "http://127.0.0.1:8012",
      fetchImpl: async () => new Response("{not-json", { status: 200 }),
    });
    await expect(client.login("a@b.test", "x")).rejects.toMatchObject({
      code: "MALFORMED_PEER_RESPONSE",
    });
  });

  it("composition fail-closed via fetch double", async () => {
    const client = getIdentityClient(
      {
        NEXT_PUBLIC_SHELL_MODE: "real-peers",
        IDENTITY_BASE_URL: "http://127.0.0.1:8012",
      },
      {
        fetchImpl: async () => {
          throw new Error("identity peer unreachable");
        },
      },
    );
    await expect(client.resolveSession("sess-x")).rejects.toMatchObject({
      code: "PEER_UNAVAILABLE",
    });
  });

  it("maps login success and me from identity.v1 shapes", async () => {
    const client = createRealPeerIdentityClient({
      baseUrl: "http://identity.test",
      fetchImpl: async (input, init) => {
        const url = String(input);
        if (url.endsWith("/v1/auth/login") && init?.method === "POST") {
          return Response.json({
            user: {
              user_id: "user-1",
              account_type: "customer",
              email: "customer@example.test",
              display_name: "Demo",
              status: "active",
              authz_version: 1,
            },
            workspaces: [
              {
                assignment_id: "asg-1",
                tenant_id: "tenant-demo",
                role_id: "customer",
                scope_key: "tenant-demo",
                status: "active",
              },
            ],
            active_assignment: {
              assignment_id: "asg-1",
              tenant_id: "tenant-demo",
              role_id: "customer",
              scope_key: "tenant-demo",
              status: "active",
            },
            session_token: "tok-sess-1",
            expires_at: "2099-01-01T00:00:00Z",
          });
        }
        if (url.endsWith("/v1/auth/me")) {
          return Response.json({
            user: {
              user_id: "user-1",
              account_type: "customer",
              email: "customer@example.test",
              display_name: "Demo",
              preferred_language: "en",
              email_verified_at: null,
              status: "active",
              authz_version: 1,
            },
            workspaces: [
              {
                assignment_id: "asg-1",
                tenant_id: "tenant-demo",
                role_id: "customer",
                scope_key: "tenant-demo",
                status: "active",
              },
            ],
            active_assignment: {
              assignment_id: "asg-1",
              tenant_id: "tenant-demo",
              role_id: "customer",
              scope_key: "tenant-demo",
              status: "active",
            },
            permissions: ["identity.self.read"],
          });
        }
        return new Response("not found", { status: 404 });
      },
    });
    const login = await client.login("customer@example.test", "x");
    expect(login.ok).toBe(true);
    if (!login.ok) return;
    expect(login.session.session_id).toBe("tok-sess-1");
    expect(login.workspaces[0]?.role).toBe("customer");
    const me = await client.resolveSession("tok-sess-1");
    expect(me?.user.user_id).toBe("user-1");
    expect(me?.assignment.role).toBe("customer");
  });

  it("getMe / patchProfile / notifications / challenges hit identity.v1 paths", async () => {
    const calls: Array<{ url: string; method: string; body?: unknown }> = [];
    const client = createRealPeerIdentityClient({
      baseUrl: "http://identity.test",
      fetchImpl: async (input, init) => {
        const url = String(input);
        const method = init?.method ?? "GET";
        const body = init?.body ? JSON.parse(String(init.body)) : undefined;
        calls.push({ url, method, body });
        if (url.endsWith("/v1/auth/me") && method === "GET") {
          return Response.json({
            user: {
              user_id: "user-1",
              account_type: "customer",
              email: "customer@example.test",
              display_name: "Demo",
              preferred_language: "en",
              email_verified_at: null,
              status: "active",
              authz_version: 1,
            },
            workspaces: [
              {
                assignment_id: "asg-1",
                tenant_id: "tenant-demo",
                role_id: "customer",
                scope_key: "tenant-demo",
                status: "active",
              },
            ],
            active_assignment: {
              assignment_id: "asg-1",
              tenant_id: "tenant-demo",
              role_id: "customer",
              scope_key: "tenant-demo",
              status: "active",
            },
            permissions: ["identity.self.read"],
          });
        }
        if (url.endsWith("/v1/auth/me") && method === "PATCH") {
          return Response.json({
            user: {
              user_id: "user-1",
              account_type: "customer",
              email: "customer@example.test",
              display_name: body.display_name,
              preferred_language: body.preferred_language ?? "en",
              email_verified_at: null,
              status: "active",
              authz_version: 1,
            },
          });
        }
        if (url.endsWith("/v1/auth/notifications") && method === "GET") {
          return Response.json({
            notifications: [
              {
                notification_id: "ntf-1",
                title: "Welcome",
                body: "Hello",
                created_at: "2026-11-15T00:00:00Z",
                read_at: null,
              },
            ],
          });
        }
        if (url.endsWith("/v1/auth/notifications/ntf-1/read")) {
          return Response.json({
            notification_id: "ntf-1",
            read_at: "2026-11-15T01:00:00Z",
          });
        }
        if (url.endsWith("/v1/auth/workspaces") && method === "GET") {
          return Response.json({
            workspaces: [
              {
                assignment_id: "asg-1",
                tenant_id: "tenant-demo",
                role_id: "customer",
                scope_key: "tenant-demo",
                status: "active",
              },
            ],
            active_assignment: {
              assignment_id: "asg-1",
              tenant_id: "tenant-demo",
              role_id: "customer",
              scope_key: "tenant-demo",
              status: "active",
            },
          });
        }
        if (url.endsWith("/v1/auth/workspaces/select")) {
          return Response.json({
            session_token: "tok-next",
            expires_at: "2099-01-01T00:00:00Z",
            active_assignment: {
              assignment_id: "asg-1",
              tenant_id: "tenant-demo",
              role_id: "customer",
              scope_key: "tenant-demo",
              status: "active",
            },
          });
        }
        if (url.endsWith("/v1/auth/verify/request")) {
          return Response.json({ status: "accepted" }, { status: 202 });
        }
        if (url.endsWith("/v1/auth/verify/confirm")) {
          return Response.json({
            user: {
              user_id: "user-1",
              account_type: "customer",
              email: "customer@example.test",
              display_name: "Demo",
              preferred_language: "en",
              email_verified_at: "2026-11-15T02:00:00Z",
              status: "active",
              authz_version: 1,
            },
            email_verified: true,
          });
        }
        if (url.endsWith("/v1/auth/mfa/challenge")) {
          return Response.json(
            { status: "accepted", sandbox_code: "ABCD1234" },
            { status: 202 },
          );
        }
        if (url.endsWith("/v1/auth/mfa/verify")) {
          return Response.json({
            mfa_verified: true,
            mfa_verified_at: "2026-11-15T03:00:00Z",
          });
        }
        if (url.endsWith("/v1/auth/password/forgot")) {
          return Response.json({ status: "accepted" }, { status: 202 });
        }
        if (url.endsWith("/v1/auth/password/reset")) {
          return Response.json({ status: "reset" });
        }
        return new Response("not found", { status: 404 });
      },
    });

    const me = await client.getMe("tok");
    expect(me?.user.preferred_language).toBe("en");
    expect(me?.user.display_name).toBe("Demo");

    const patched = await client.patchProfile("tok", {
      display_name: "Updated",
      preferred_language: "es",
    });
    expect(patched.user.display_name).toBe("Updated");
    expect(patched.user.preferred_language).toBe("es");

    const notes = await client.listNotifications("tok");
    expect(notes.notifications).toHaveLength(1);
    expect(notes.notifications[0]?.notification_id).toBe("ntf-1");

    const marked = await client.markNotificationRead("tok", "ntf-1");
    expect(marked.read_at).toBe("2026-11-15T01:00:00Z");

    const workspaces = await client.listWorkspaces("tok");
    expect(workspaces.workspaces[0]?.role).toBe("customer");

    const selected = await client.selectWorkspace("tok", "asg-1");
    expect(selected?.session_id).toBe("tok-next");

    await expect(client.requestVerify("tok")).resolves.toMatchObject({
      status: "accepted",
    });
    const confirmed = await client.confirmVerify("tok", "code-1");
    expect(confirmed.email_verified).toBe(true);

    const mfa = await client.mfaChallenge("tok");
    expect(mfa.status).toBe("accepted");
    expect(mfa.sandbox_code).toBe("ABCD1234");
    await expect(client.mfaVerify("tok", "ABCD1234")).resolves.toMatchObject({
      mfa_verified: true,
    });

    await expect(
      client.forgotPassword("customer@example.test"),
    ).resolves.toMatchObject({ status: "accepted" });
    await expect(
      client.resetPassword({
        email: "customer@example.test",
        code: "reset-1",
        new_password: "password99",
      }),
    ).resolves.toMatchObject({ status: "reset" });

    expect(calls.map((c) => `${c.method} ${c.url}`)).toEqual(
      expect.arrayContaining([
        "GET http://identity.test/v1/auth/me",
        "PATCH http://identity.test/v1/auth/me",
        "GET http://identity.test/v1/auth/notifications",
        "POST http://identity.test/v1/auth/notifications/ntf-1/read",
        "GET http://identity.test/v1/auth/workspaces",
        "POST http://identity.test/v1/auth/workspaces/select",
        "POST http://identity.test/v1/auth/verify/request",
        "POST http://identity.test/v1/auth/verify/confirm",
        "POST http://identity.test/v1/auth/mfa/challenge",
        "POST http://identity.test/v1/auth/mfa/verify",
        "POST http://identity.test/v1/auth/password/forgot",
        "POST http://identity.test/v1/auth/password/reset",
      ]),
    );
  });

  it("forgotPassword never invents success from peer failure", async () => {
    const client = createRealPeerIdentityClient({
      baseUrl: "http://identity.test",
      fetchImpl: async () => {
        throw new Error("peer down");
      },
    });
    await expect(client.forgotPassword("a@b.test")).rejects.toMatchObject({
      code: "PEER_UNAVAILABLE",
    });
  });
});

describe("fixture identity auth surface", () => {
  beforeEach(() => {
    resetSharedIdentityStub();
    resetIdentityClientCache();
  });

  it("fixture client supports profile, notifications, challenges, workspaces", async () => {
    const client = getIdentityClient({ NEXT_PUBLIC_SHELL_MODE: "fixture" });
    const login = await client.login("customer@example.test", "demo-customer");
    expect(login.ok).toBe(true);
    if (!login.ok) return;
    const token = login.session.session_id;

    const me = await client.getMe(token);
    expect(me?.user.email).toBe("customer@example.test");

    const patched = await client.patchProfile(token, {
      display_name: "Patched Customer",
      preferred_language: "fr",
    });
    expect(patched.user.display_name).toBe("Patched Customer");
    expect(patched.user.preferred_language).toBe("fr");

    const notes = await client.listNotifications(token);
    expect(notes.notifications.length).toBeGreaterThanOrEqual(1);

    const first = notes.notifications[0]!;
    const marked = await client.markNotificationRead(
      token,
      first.notification_id,
    );
    expect(marked.read_at).toBeTruthy();

    const workspaces = await client.listWorkspaces(token);
    expect(workspaces.workspaces.map((w) => w.role)).toEqual(["customer"]);

    await expect(client.requestVerify(token)).resolves.toMatchObject({
      status: "accepted",
    });
    const confirm = await client.confirmVerify(token, "fixture-verify");
    expect(confirm.email_verified).toBe(true);

    const challenge = await client.mfaChallenge(token);
    expect(challenge.status).toBe("accepted");
    expect(typeof challenge.sandbox_code).toBe("string");
    await expect(
      client.mfaVerify(token, challenge.sandbox_code!),
    ).resolves.toMatchObject({ mfa_verified: true });

    await expect(
      client.forgotPassword("customer@example.test"),
    ).resolves.toMatchObject({ status: "accepted" });
    await expect(
      client.resetPassword({
        email: "customer@example.test",
        code: "fixture-reset",
        new_password: "demo-customer-2",
      }),
    ).resolves.toMatchObject({ status: "reset" });
  });
});
