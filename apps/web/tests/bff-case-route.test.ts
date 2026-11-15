import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("next/headers", () => ({
  cookies: vi.fn(),
}));

import { cookies } from "next/headers";
import { GET } from "@/app/api/bff/case/[...path]/route";
import { SESSION_COOKIE } from "@/lib/server/auth";

describe("BFF /api/bff/case route auth", () => {
  const originalFetch = globalThis.fetch;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    process.env.CASE_API_BASE_URL = "http://case.test";
    process.env.CASE_API_BEARER_TOKEN = "tok-service";
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    delete process.env.CASE_API_BASE_URL;
    delete process.env.CASE_API_BEARER_TOKEN;
  });

  it("unauthenticated request returns 401 and does not call upstream with CASE_API_BEARER_TOKEN", async () => {
    vi.mocked(cookies).mockResolvedValue({
      get: () => undefined,
    } as Awaited<ReturnType<typeof cookies>>);

    const res = await GET(new NextRequest("http://localhost/api/bff/case/v1/cases"), {
      params: Promise.resolve({ path: ["v1", "cases"] }),
    });

    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body.code).toBe("UNAUTHORIZED");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("authenticated request forwards sentinel_session, not CASE_API_BEARER_TOKEN", async () => {
    vi.mocked(cookies).mockResolvedValue({
      get: (name: string) =>
        name === SESSION_COOKIE ? { name: SESSION_COOKIE, value: "sess-user" } : undefined,
    } as Awaited<ReturnType<typeof cookies>>);

    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const res = await GET(new NextRequest("http://localhost/api/bff/case/v1/cases"), {
      params: Promise.resolve({ path: ["v1", "cases"] }),
    });

    expect(res.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer sess-user");
    expect(headers.get("Authorization")).not.toContain("tok-service");
  });
});
