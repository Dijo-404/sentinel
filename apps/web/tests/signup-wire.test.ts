import { describe, expect, it } from "vitest";
import { createRealPeerIdentityClient } from "@/adapters/real-peer-identity-client";
import { createIdentityStub } from "./stubs/identity";

const body = {
  email: "new@example.test",
  display_name: "New User",
  password: "password1",
  language: "hi",
};
describe("public registration wire contract", () => {
  it.each(["customer", "merchant"] as const)(
    "sends %s registration only to its own endpoint",
    async (type) => {
      let sent: { url: string; body: unknown } | undefined;
      const client = createRealPeerIdentityClient({
        baseUrl: "http://identity.test",
        fetchImpl: async (url, init) => {
          sent = { url: String(url), body: JSON.parse(String(init?.body)) };
          return Response.json(
            {
              user: {
                user_id: "new-user",
                email: body.email,
                display_name: body.display_name,
                account_type: type === "merchant" ? "staff" : "customer",
                status: "active",
              },
              session_token: "secret-session",
              expires_at: "2099-01-01T00:00:00Z",
              assignment: {
                assignment_id: "a-new",
                tenant_id: "tenant-demo",
                role_id: type,
                status: "active",
                scope_key: "tenant-demo",
              },
              workspaces: [
                {
                  assignment_id: "a-new",
                  tenant_id: "tenant-demo",
                  role_id: type,
                  status: "active",
                  scope_key: "tenant-demo",
                },
              ],
            },
            { status: 201 },
          );
        },
      });
      const result =
        type === "merchant"
          ? await client.registerMerchant({ ...body, business_name: "Shop" })
          : await client.registerCustomer(body);
      expect(result.ok).toBe(true);
      expect(sent).toEqual({
        url: `http://identity.test/v1/auth/${type}/register`,
        body: {
          email: body.email,
          display_name: body.display_name,
          password: body.password,
          preferred_language: "hi",
          ...(type === "merchant" ? { business_name: "Shop" } : {}),
        },
      });
      if (result.ok)
        expect(result.user.account_class).toBe(type === "merchant" ? "staff" : "customer");
    },
  );
  it("maps ACCOUNT_NOT_FOUND distinctly from generic 401 and rate-limited responses", async () => {
    for (const [code, status, expected] of [
      ["ACCOUNT_NOT_FOUND", 401, "ACCOUNT_NOT_FOUND"],
      ["UNAUTHORIZED", 401, "INVALID_CREDENTIALS"],
      ["RATE_LIMITED", 429, "RATE_LIMITED"],
    ] as const) {
      const client = createRealPeerIdentityClient({
        baseUrl: "http://identity.test",
        fetchImpl: async () =>
          Response.json({ code, message: "Failure", request_id: "test" }, { status }),
      });
      expect(await client.login(body.email, body.password)).toEqual({ ok: false, code: expected });
    }
  });
  it.each([
    ["INVALID_INPUT", 422],
    ["VALIDATION_ERROR", 422],
    ["INVALID_INPUT", 400],
  ] as const)(
    "maps login validation rejection %s/%s to invalid credentials",
    async (code, status) => {
      const client = createRealPeerIdentityClient({
        baseUrl: "http://identity.test",
        fetchImpl: async () =>
          Response.json({ code, message: "Invalid login input", request_id: "test" }, { status }),
      });
      expect(await client.login(body.email, body.password)).toEqual({
        ok: false,
        code: "INVALID_CREDENTIALS",
      });
    },
  );
  it.each([500, 503])("keeps identity login outages visible for HTTP %s", async (status) => {
    const client = createRealPeerIdentityClient({
      baseUrl: "http://identity.test",
      fetchImpl: async () =>
        Response.json(
          { code: "PEER_UNAVAILABLE", message: "Identity unavailable", request_id: "test" },
          { status },
        ),
    });
    await expect(client.login(body.email, body.password)).rejects.toMatchObject({
      code: "PEER_UNAVAILABLE",
      httpStatus: status,
    });
  });
  it("keeps a malformed 422 login response visible as a peer error", async () => {
    const client = createRealPeerIdentityClient({
      baseUrl: "http://identity.test",
      fetchImpl: async () => new Response("invalid JSON", { status: 422 }),
    });
    await expect(client.login(body.email, body.password)).rejects.toMatchObject({
      code: "MALFORMED_PEER_RESPONSE",
      httpStatus: 422,
    });
  });
  it("fixture merchant registration assigns only merchant with generated scope and duplicate rejection", () => {
    const stub = createIdentityStub();
    const result = stub.registerMerchant({ ...body, business_name: "Shop" });
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.user.account_class).toBe("staff");
    expect(result.user.assignments).toEqual([
      expect.objectContaining({
        role: "merchant",
        scope: { merchant_ref: expect.stringMatching(/^merchant-/) },
      }),
    ]);
    expect(stub.registerCustomer(body)).toEqual({ ok: false, code: "ALREADY_EXISTS" });
    expect(stub.registerMerchant({ ...body, email: "invalid", business_name: "Shop" })).toEqual({
      ok: false,
      code: "INVALID_INPUT",
    });
    expect(
      stub.registerMerchant({
        ...body,
        email: "x@example.test",
        business_name: "Shop",
        roles: ["admin"],
      }),
    ).toEqual({ ok: false, code: "PRIVILEGED_FIELDS_REJECTED" });
  });
});
