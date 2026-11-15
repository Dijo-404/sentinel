import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("next/headers", () => ({
  cookies: vi.fn(),
}));

import { cookies } from "next/headers";
import { POST as voicePost } from "@/app/api/bff/voice/[...path]/route";
import { SESSION_COOKIE } from "@/lib/server/auth";

describe("BFF voice peer proxy", () => {
  const originalFetch = globalThis.fetch;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    process.env.VOICE_BASE_URL = "http://voice.test";
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    delete process.env.VOICE_BASE_URL;
  });

  function mockSession() {
    vi.mocked(cookies).mockResolvedValue({
      get: (name: string) =>
        name === SESSION_COOKIE ? { name: SESSION_COOKIE, value: "sess-user" } : undefined,
    } as Awaited<ReturnType<typeof cookies>>);
  }

  it("POST /v1/transcribe forwards session bearer", async () => {
    mockSession();
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          original_text: "paid twice",
          language: "en-IN",
          ambiguous: false,
          reason_codes: [],
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      ),
    );

    const res = await voicePost(
      new NextRequest("http://localhost/api/bff/voice/v1/transcribe", {
        method: "POST",
        body: JSON.stringify({
          language: "en-IN",
          text: "paid twice",
          consent: true,
        }),
        headers: { "content-type": "application/json" },
      }),
      { params: Promise.resolve({ path: ["v1", "transcribe"] }) },
    );

    expect(res.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://voice.test/v1/transcribe");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer sess-user");
  });

  it("missing VOICE_BASE_URL returns 503 — fail visible", async () => {
    mockSession();
    delete process.env.VOICE_BASE_URL;

    const res = await voicePost(
      new NextRequest("http://localhost/api/bff/voice/v1/transcribe", {
        method: "POST",
        body: "{}",
        headers: { "content-type": "application/json" },
      }),
      { params: Promise.resolve({ path: ["v1", "transcribe"] }) },
    );

    expect(res.status).toBe(503);
    const body = (await res.json()) as { code: string };
    expect(body.code).toBe("PEER_UNAVAILABLE");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("missing session returns 401 — no peer call", async () => {
    vi.mocked(cookies).mockResolvedValue({
      get: () => undefined,
    } as Awaited<ReturnType<typeof cookies>>);

    const res = await voicePost(
      new NextRequest("http://localhost/api/bff/voice/v1/transcribe", {
        method: "POST",
        body: "{}",
        headers: { "content-type": "application/json" },
      }),
      { params: Promise.resolve({ path: ["v1", "transcribe"] }) },
    );

    expect(res.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
