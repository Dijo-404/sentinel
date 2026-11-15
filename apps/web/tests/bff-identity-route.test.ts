import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("next/headers", () => ({
  cookies: vi.fn(),
}));

import { cookies } from "next/headers";
import { GET, PATCH, POST } from "@/app/api/bff/identity/[...path]/route";
import { SESSION_COOKIE } from "@/lib/server/auth";

describe("BFF /api/bff/identity passthrough", () => {
  const originalFetch = globalThis.fetch;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    process.env.IDENTITY_BASE_URL = "http://identity.test";
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    delete process.env.IDENTITY_BASE_URL;
  });

  it("PATCH /v1/auth/me forwards session bearer to identity peer", async () => {
    vi.mocked(cookies).mockResolvedValue({
      get: (name: string) =>
        name === SESSION_COOKIE ? { name: SESSION_COOKIE, value: "sess-user" } : undefined,
    } as Awaited<ReturnType<typeof cookies>>);

    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          user: {
            user_id: "user-1",
            display_name: "Updated",
            preferred_language: "en",
          },
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const res = await PATCH(
      new NextRequest("http://localhost/api/bff/identity/v1/auth/me", {
        method: "PATCH",
        body: JSON.stringify({ display_name: "Updated" }),
        headers: { "content-type": "application/json" },
      }),
      { params: Promise.resolve({ path: ["v1", "auth", "me"] }) },
    );

    expect(res.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://identity.test/v1/auth/me");
    expect(init.method).toBe("PATCH");
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBe("Bearer sess-user");
  });

  it("GET notifications and POST forgot forward without inventing rows", async () => {
    vi.mocked(cookies).mockResolvedValue({
      get: (name: string) =>
        name === SESSION_COOKIE ? { name: SESSION_COOKIE, value: "sess-user" } : undefined,
    } as Awaited<ReturnType<typeof cookies>>);

    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ notifications: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const list = await GET(
      new NextRequest("http://localhost/api/bff/identity/v1/auth/notifications"),
      {
        params: Promise.resolve({
          path: ["v1", "auth", "notifications"],
        }),
      },
    );
    expect(list.status).toBe(200);
    expect(String(fetchMock.mock.calls[0]![0])).toContain("/v1/auth/notifications");

    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ status: "accepted" }), {
        status: 202,
        headers: { "content-type": "application/json" },
      }),
    );

    const forgot = await POST(
      new NextRequest("http://localhost/api/bff/identity/v1/auth/password/forgot", {
        method: "POST",
        body: JSON.stringify({ email: "a@b.test" }),
        headers: { "content-type": "application/json" },
      }),
      {
        params: Promise.resolve({
          path: ["v1", "auth", "password", "forgot"],
        }),
      },
    );
    expect(forgot.status).toBe(202);
    expect(String(fetchMock.mock.calls[1]![0])).toContain("/v1/auth/password/forgot");
  });

  it("unauthenticated identity BFF returns 401", async () => {
    vi.mocked(cookies).mockResolvedValue({
      get: () => undefined,
    } as Awaited<ReturnType<typeof cookies>>);

    const res = await GET(new NextRequest("http://localhost/api/bff/identity/v1/auth/me"), {
      params: Promise.resolve({ path: ["v1", "auth", "me"] }),
    });
    expect(res.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
