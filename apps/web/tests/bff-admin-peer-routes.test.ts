import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("next/headers", () => ({
  cookies: vi.fn(),
}));

import { cookies } from "next/headers";
import { GET as evalsGet } from "@/app/api/bff/evals/[...path]/route";
import { GET as observabilityGet } from "@/app/api/bff/observability/[...path]/route";
import { GET as platformAiGet } from "@/app/api/bff/platform-ai/[...path]/route";
import { GET as policyGet } from "@/app/api/bff/policy/[...path]/route";
import { GET as identityGet } from "@/app/api/bff/identity/[...path]/route";
import { GET as merchantTeamsGet } from "@/app/api/bff/merchant-teams/[...path]/route";
import { SESSION_COOKIE } from "@/lib/server/auth";

describe("BFF admin peer proxies", () => {
  const originalFetch = globalThis.fetch;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    process.env.EVALS_BASE_URL = "http://evals.test";
    process.env.OBSERVABILITY_BASE_URL = "http://observability.test";
    process.env.PLATFORM_AI_BASE_URL = "http://platform-ai.test";
    process.env.POLICY_BASE_URL = "http://policy.test";
    process.env.IDENTITY_BASE_URL = "http://identity.test";
    process.env.MERCHANT_TEAMS_BASE_URL = "http://merchant-teams.test";
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    delete process.env.EVALS_BASE_URL;
    delete process.env.OBSERVABILITY_BASE_URL;
    delete process.env.PLATFORM_AI_BASE_URL;
    delete process.env.POLICY_BASE_URL;
    delete process.env.IDENTITY_BASE_URL;
    delete process.env.MERCHANT_TEAMS_BASE_URL;
  });

  function mockSession() {
    vi.mocked(cookies).mockResolvedValue({
      get: (name: string) =>
        name === SESSION_COOKIE ? { name: SESSION_COOKIE, value: "sess-admin" } : undefined,
    } as Awaited<ReturnType<typeof cookies>>);
  }

  function mockUnauth() {
    vi.mocked(cookies).mockResolvedValue({
      get: () => undefined,
    } as Awaited<ReturnType<typeof cookies>>);
  }

  it("evals GET /v1/reports forwards session bearer", async () => {
    mockSession();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ reports: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const res = await evalsGet(new NextRequest("http://localhost/api/bff/evals/v1/reports"), {
      params: Promise.resolve({ path: ["v1", "reports"] }),
    });

    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://evals.test/v1/reports");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer sess-admin");
  });

  it("observability GET /v1/signals forwards session bearer", async () => {
    mockSession();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ signals: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const res = await observabilityGet(
      new NextRequest("http://localhost/api/bff/observability/v1/signals"),
      { params: Promise.resolve({ path: ["v1", "signals"] }) },
    );

    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://observability.test/v1/signals");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer sess-admin");
  });

  it("platform-ai GET /v1/config forwards session bearer", async () => {
    mockSession();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ config: {} }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const res = await platformAiGet(
      new NextRequest("http://localhost/api/bff/platform-ai/v1/config"),
      { params: Promise.resolve({ path: ["v1", "config"] }) },
    );

    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://platform-ai.test/v1/config");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer sess-admin");
  });

  it("policy GET /v1/policies forwards session bearer", async () => {
    mockSession();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ policies: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const res = await policyGet(new NextRequest("http://localhost/api/bff/policy/v1/policies"), {
      params: Promise.resolve({ path: ["v1", "policies"] }),
    });

    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://policy.test/v1/policies");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer sess-admin");
  });

  it("identity admin path passthrough (GET /v1/admin/tenants)", async () => {
    mockSession();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ tenants: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const res = await identityGet(
      new NextRequest("http://localhost/api/bff/identity/v1/admin/tenants"),
      { params: Promise.resolve({ path: ["v1", "admin", "tenants"] }) },
    );

    expect(res.status).toBe(200);
    expect(String(fetchMock.mock.calls[0]![0])).toBe("http://identity.test/v1/admin/tenants");
  });

  it("merchant-teams admin merchants passthrough", async () => {
    mockSession();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ merchants: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const res = await merchantTeamsGet(
      new NextRequest("http://localhost/api/bff/merchant-teams/v1/admin/merchants"),
      { params: Promise.resolve({ path: ["v1", "admin", "merchants"] }) },
    );

    expect(res.status).toBe(200);
    expect(String(fetchMock.mock.calls[0]![0])).toBe(
      "http://merchant-teams.test/v1/admin/merchants",
    );
  });

  it.each([
    ["evals", evalsGet, ["v1", "reports"]],
    ["observability", observabilityGet, ["v1", "signals"]],
    ["platform-ai", platformAiGet, ["v1", "config"]],
    ["policy", policyGet, ["v1", "policies"]],
  ] as const)("%s missing session returns 401 — no peer call", async (_label, handler, path) => {
    mockUnauth();
    const res = await handler(
      new NextRequest(`http://localhost/api/bff/${_label}/${path.join("/")}`),
      { params: Promise.resolve({ path: [...path] }) },
    );
    expect(res.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
