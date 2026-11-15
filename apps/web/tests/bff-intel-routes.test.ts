import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("next/headers", () => ({
  cookies: vi.fn(),
}));

import { cookies } from "next/headers";
import { GET as assistantGet } from "@/app/api/bff/assistant/[...path]/route";
import { GET as knowledgeGet } from "@/app/api/bff/knowledge/[...path]/route";
import { GET as opsActivityGet } from "@/app/api/bff/ops-activity/[...path]/route";
import { SESSION_COOKIE } from "@/lib/server/auth";

describe("BFF intel peer proxies", () => {
  const originalFetch = globalThis.fetch;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    process.env.ASSISTANT_BASE_URL = "http://assistant.test";
    process.env.KNOWLEDGE_BASE_URL = "http://knowledge.test";
    process.env.OPS_ACTIVITY_BASE_URL = "http://ops-activity.test";
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    delete process.env.ASSISTANT_BASE_URL;
    delete process.env.KNOWLEDGE_BASE_URL;
    delete process.env.OPS_ACTIVITY_BASE_URL;
  });

  function mockSession() {
    vi.mocked(cookies).mockResolvedValue({
      get: (name: string) =>
        name === SESSION_COOKIE ? { name: SESSION_COOKIE, value: "sess-user" } : undefined,
    } as Awaited<ReturnType<typeof cookies>>);
  }

  it("assistant GET /v1/threads forwards session bearer", async () => {
    mockSession();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ threads: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const res = await assistantGet(
      new NextRequest("http://localhost/api/bff/assistant/v1/threads?role=operator"),
      { params: Promise.resolve({ path: ["v1", "threads"] }) },
    );

    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://assistant.test/v1/threads?role=operator");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer sess-user");
  });

  it("knowledge GET /v1/articles forwards session bearer", async () => {
    mockSession();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ articles: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const res = await knowledgeGet(
      new NextRequest("http://localhost/api/bff/knowledge/v1/articles"),
      { params: Promise.resolve({ path: ["v1", "articles"] }) },
    );

    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://knowledge.test/v1/articles");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer sess-user");
  });

  it("ops-activity GET /v1/activity forwards session bearer", async () => {
    mockSession();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ items: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const res = await opsActivityGet(
      new NextRequest("http://localhost/api/bff/ops-activity/v1/activity"),
      { params: Promise.resolve({ path: ["v1", "activity"] }) },
    );

    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://ops-activity.test/v1/activity");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer sess-user");
  });

  it("missing session returns 401 — no peer call", async () => {
    vi.mocked(cookies).mockResolvedValue({
      get: () => undefined,
    } as Awaited<ReturnType<typeof cookies>>);

    const res = await knowledgeGet(
      new NextRequest("http://localhost/api/bff/knowledge/v1/articles"),
      { params: Promise.resolve({ path: ["v1", "articles"] }) },
    );

    expect(res.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
