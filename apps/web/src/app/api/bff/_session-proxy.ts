import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/server/auth";

export type SessionProxyConfig = {
  /** Server-only env var holding the upstream base URL. */
  envKey: string;
  peerLabel: string;
  requestIdPrefix: string;
};

/**
 * Portal BFF: forward to a peer with the caller's sentinel_session.
 * Never falls back to a service token. Failures stay visible.
 */
export function createSessionPeerProxy(config: SessionProxyConfig) {
  async function proxy(
    req: NextRequest,
    ctx: { params: Promise<{ path: string[] }> },
  ): Promise<NextResponse> {
    const { path } = await ctx.params;
    const jar = await cookies();
    const bearer = jar.get(SESSION_COOKIE)?.value;
    if (!bearer) {
      return NextResponse.json(
        {
          code: "UNAUTHORIZED",
          message: "Missing sentinel_session; sign in required",
          request_id: `${config.requestIdPrefix}-unauth`,
        },
        { status: 401 },
      );
    }

    const base = (process.env[config.envKey] ?? "").replace(/\/$/, "");
    if (!base) {
      return NextResponse.json(
        {
          code: "PEER_UNAVAILABLE",
          message: `${config.envKey} is required in real-peers mode`,
          request_id: `${config.requestIdPrefix}-missing-base`,
        },
        { status: 503 },
      );
    }

    const suffix = path.map(encodeURIComponent).join("/");
    const target = `${base}/${suffix}${req.nextUrl.search}`;
    const requestId =
      req.headers.get("x-request-id") ??
      `${config.requestIdPrefix}-${crypto.randomUUID()}`;

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
            err instanceof Error
              ? err.message
              : `Network failure contacting ${config.peerLabel}`,
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
        "X-Request-Id": upstream.headers.get("x-request-id") ?? requestId,
      },
    });
  }

  return {
    GET: proxy,
    POST: proxy,
    PUT: proxy,
    PATCH: proxy,
    DELETE: proxy,
  };
}
