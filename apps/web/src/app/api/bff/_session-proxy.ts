import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/server/auth";
import { identityRoleToPortal } from "@/lib/server/identity-roles";
import type { PortalRole } from "../../../../tests/stubs/identity";

export type SessionProxyConfig = {
  /** Server-only env var holding the upstream base URL. */
  envKey: string;
  peerLabel: string;
  requestIdPrefix: string;
  /**
   * Optional server-only env var for the upstream bearer (e.g. voice peer principal).
   * Session cookie is still required to call the BFF; never put this in NEXT_PUBLIC_*.
   */
  upstreamTokenEnvKey?: string;
  /**
   * Optional prefix for role-scoped upstream tokens, e.g. "ASSISTANT_TOKEN_".
   * When set, BFF resolves active portal role via identity /me and uses
   * process.env[`${prefix}${portalRole}`] when present, else upstreamTokenEnvKey.
   */
  upstreamTokenRolePrefix?: string;
};

/**
 * Portal BFF: forward to a peer with the caller's sentinel_session.
 * Optional upstreamTokenEnvKey / role prefix swaps only the upstream Authorization
 * (session still required). Failures stay visible — no silent fixture fallback.
 */
export function createSessionPeerProxy(config: SessionProxyConfig) {
  async function proxy(
    req: NextRequest,
    ctx: { params: Promise<{ path: string[] }> },
  ): Promise<NextResponse> {
    const { path } = await ctx.params;
    const jar = await cookies();
    const sessionBearer = jar.get(SESSION_COOKIE)?.value;
    if (!sessionBearer) {
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

    const bearer = await resolveUpstreamBearer(config, sessionBearer);

    const suffix = path.map(encodeURIComponent).join("/");
    const target = `${base}/${suffix}${req.nextUrl.search}`;
    const requestId =
      req.headers.get("x-request-id") ?? `${config.requestIdPrefix}-${crypto.randomUUID()}`;

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
        req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer();

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
            err instanceof Error ? err.message : `Network failure contacting ${config.peerLabel}`,
          request_id: requestId,
        },
        { status: 503 },
      );
    }

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") ?? "application/json",
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

async function resolveUpstreamBearer(
  config: SessionProxyConfig,
  sessionBearer: string,
): Promise<string> {
  const fallback = config.upstreamTokenEnvKey
    ? (process.env[config.upstreamTokenEnvKey] ?? "").trim()
    : "";

  if (config.upstreamTokenRolePrefix) {
    const role = await resolvePortalRole(sessionBearer);
    if (role) {
      const keyed = (process.env[`${config.upstreamTokenRolePrefix}${role}`] ?? "").trim();
      if (keyed) return keyed;
    }
  }

  return fallback || sessionBearer;
}

async function resolvePortalRole(sessionBearer: string): Promise<PortalRole | null> {
  const identityBase = (process.env.IDENTITY_BASE_URL ?? "").replace(/\/$/, "");
  if (!identityBase) return null;
  try {
    const res = await fetch(`${identityBase}/v1/auth/me`, {
      headers: {
        Authorization: `Bearer ${sessionBearer}`,
        Accept: "application/json",
      },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const body = (await res.json()) as {
      active_assignment?: { role_id?: string } | null;
    };
    const roleId = body.active_assignment?.role_id;
    if (typeof roleId !== "string" || !roleId) return null;
    return identityRoleToPortal(roleId);
  } catch {
    return null;
  }
}
