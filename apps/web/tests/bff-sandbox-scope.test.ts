import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => ({ value: "caller-session" }) }),
}));
import { createSessionPeerProxy } from "@/app/api/bff/_session-proxy";

const grant = { tenant_id: "tenant-demo", role_id: "merchant", merchant_ref: "merchant-demo-1" };
const proxy = createSessionPeerProxy({
  envKey: "QA_PEER_URL",
  peerLabel: "QA",
  requestIdPrefix: "qa",
  upstreamTokenEnvKey: "QA_PEER_TOKEN",
  upstreamTokenRoles: ["merchant"],
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});
describe("sandbox peer token binding", () => {
  it.each([
    ["seed-user", grant, "1", 200, "sandbox-token"],
    ["new-user", grant, "1", 200, "caller-session"],
    ["seed-user", { ...grant, tenant_id: "other-tenant" }, "1", 200, "caller-session"],
    ["seed-user", { ...grant, merchant_ref: "other-merchant" }, "1", 200, "caller-session"],
    ["seed-user", { ...grant, role_id: "customer" }, "1", 200, "caller-session"],
    ["seed-user", grant, "0", 200, "caller-session"],
    ["seed-user", grant, "1", 401, "caller-session"],
  ])(
    "binds shared token to exact sandbox user, tenant, role and merchant (%s, %j)",
    async (id, active, sandbox, status, bearer) => {
      vi.stubEnv("QA_PEER_URL", "http://peer.test");
      vi.stubEnv("QA_PEER_TOKEN", "sandbox-token");
      vi.stubEnv("IDENTITY_BASE_URL", "http://identity.test");
      vi.stubEnv("SENTINEL_V1_SANDBOX", sandbox);
      vi.stubEnv("WEB_SANDBOX_PEER_BINDINGS", JSON.stringify({ "seed-user": grant }));
      const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
        if (url.startsWith("http://identity.test"))
          return Response.json({ user: { user_id: id }, active_assignment: active }, { status });
        expect(new Headers(init?.headers).get("Authorization")).toBe(`Bearer ${bearer}`);
        return Response.json({ ok: true });
      });
      vi.stubGlobal("fetch", fetchMock);
      const res = await proxy.GET(new NextRequest("http://localhost/api/bff/qa/v1/data"), {
        params: Promise.resolve({ path: ["v1", "data"] }),
      });
      expect(res.status).toBe(200);
      expect(fetchMock).toHaveBeenCalled();
    },
  );
});
