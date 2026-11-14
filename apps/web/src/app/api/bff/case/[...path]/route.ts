import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/server/auth";

export const dynamic = "force-dynamic";

/**
 * Portal BFF: forward case-api.v1 with the caller's identity session.
 * Never uses process-wide CASE_API_BEARER_TOKEN for portal users.
 * Optional CASE_API_BEARER_TOKEN is service-only fallback when no cookie.
 */
async function proxy(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
): Promise<NextResponse> {
  const { path } = await ctx.params;
  const jar = await cookies();
  const session = jar.get(SESSION_COOKIE)?.value;
  const serviceToken = process.env.CASE_API_BEARER_TOKEN;
  const bearer = session ?? serviceToken;
  if (!bearer) {
    return NextResponse.json(
      {
        code: "UNAUTHORIZED",
        message: "Missing sentinel_session; sign in required",
        request_id: "web-bff-unauth",
      },
      { status: 401 },
    );
  }

  const base = (process.env.CASE_API_BASE_URL ?? "").replace(/\/$/, "");
  if (!base) {
    return NextResponse.json(
      {
        code: "PEER_UNAVAILABLE",
        message: "CASE_API_BASE_URL is required in real-peers mode",
        request_id: "web-bff-missing-base",
      },
      { status: 503 },
    );
  }

  const suffix = path.map(encodeURIComponent).join("/");
  const target = `${base}/${suffix}${req.nextUrl.search}`;
  const requestId =
    req.headers.get("x-request-id") ?? `web-bff-${crypto.randomUUID()}`;

  let upstream: Response;
  try {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${bearer}`,
      Accept: "application/json",
      "X-Request-Id": requestId,
    };
    const contentType = req.headers.get("content-type");
    if (contentType) headers["Content-Type"] = contentType;
    const idempotency = req.headers.get("idempotency-key");
    if (idempotency) headers["Idempotency-Key"] = idempotency;

    const body =
      req.method === "GET" || req.method === "HEAD"
        ? undefined
        : await req.arrayBuffer();

    upstream = await fetch(target, {
      method: req.method,
      headers,
      body,
      cache: "no-store",
    });
  } catch (err) {
    return NextResponse.json(
      {
        code: "PEER_UNAVAILABLE",
        message:
          err instanceof Error ? err.message : "Network failure contacting case API",
        request_id: requestId,
      },
      { status: 503 },
    );
  }

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("content-type") ?? "application/json",
      "X-Request-Id":
        upstream.headers.get("x-request-id") ?? requestId,
    },
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
