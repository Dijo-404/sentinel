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
   * process.env[`${prefix}${portalRole}`] when present. A missing role key cannot
   * borrow the shared credential unless upstreamTokenFallbackRole explicitly matches.
   */
  upstreamTokenRolePrefix?: string;
  /** Roles permitted to use this peer's explicitly bound sandbox credential. */
  upstreamTokenRoles?: PortalRole[];
  /** The single role allowed to use the shared credential when its role key is absent. */
  upstreamTokenFallbackRole?: PortalRole;
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

  const hasRoleToken =
    config.upstreamTokenRolePrefix &&
    Object.keys(process.env).some(
      (key) => key.startsWith(config.upstreamTokenRolePrefix!) && process.env[key],
    );
  if (!fallback && !hasRoleToken) return sessionBearer;
  // A shared demo token must never elevate an arbitrary logged-in account.
  if (process.env.SENTINEL_V1_SANDBOX !== "1") return sessionBearer;
  const identityBase = (process.env.IDENTITY_BASE_URL ?? "").replace(/\/$/, "");
  if (!identityBase) return sessionBearer;
  try {
    const res = await fetch(`${identityBase}/v1/auth/me`, {
      headers: { Authorization: `Bearer ${sessionBearer}`, Accept: "application/json" },
      cache: "no-store",
    });
    if (!res.ok) return sessionBearer;
    const body = await res.json();
    const active = body.active_assignment;
    const role = typeof active?.role_id === "string" ? identityRoleToPortal(active.role_id) : null;
    if (!role || !config.upstreamTokenRoles?.includes(role)) return sessionBearer;
    const bindings = JSON.parse(process.env.WEB_SANDBOX_PEER_BINDINGS ?? "{}");
    const binding =
      typeof body.user?.user_id === "string" && Object.hasOwn(bindings, body.user.user_id)
        ? bindings[body.user.user_id]
        : null;
    if (
      !binding ||
      binding.tenant_id !== active.tenant_id ||
      binding.role_id !== active.role_id ||
      (binding.merchant_ref ?? null) !== (active.merchant_ref ?? null)
    )
      return sessionBearer;
    const keyed = config.upstreamTokenRolePrefix
      ? (process.env[`${config.upstreamTokenRolePrefix}${role}`] ?? "").trim()
      : "";
    const shared =
      !config.upstreamTokenRolePrefix || config.upstreamTokenFallbackRole === role ? fallback : "";
    return keyed || shared || sessionBearer;
  } catch {
    return sessionBearer;
  }
}
