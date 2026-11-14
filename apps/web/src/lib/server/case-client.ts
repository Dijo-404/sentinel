import type { CaseClient } from "@/application/ports";
import { createCaseApiStub } from "@/adapters/fixture-case-client";
import { createRealPeerCaseClient } from "@/adapters/real-peer-case-client";
import { PeerError } from "@/domain/types";
import { readSessionId } from "./auth";

/**
 * Server-only case-api client for portal requests.
 * Real-peers forwards the per-request identity session from sentinel_session.
 * CASE_API_BEARER_TOKEN remains a service/fixture fallback when no cookie.
 */
export async function getServerCaseClient(
  env: Record<string, string | undefined> = process.env as Record<
    string,
    string | undefined
  >,
  overrides?: { fetchImpl?: typeof fetch },
): Promise<CaseClient> {
  const mode = (env.NEXT_PUBLIC_SHELL_MODE ?? "fixture") as
    | "fixture"
    | "real-peers";
  if (mode === "fixture") {
    return createCaseApiStub("valid");
  }

  const baseUrl = env.CASE_API_BASE_URL ?? "";
  if (!baseUrl) {
    throw new PeerError(
      "PEER_UNAVAILABLE",
      "CASE_API_BASE_URL is required in real-peers mode",
      "cfg-case-missing-base",
      503,
    );
  }

  const session = await readSessionId();
  const bearer = session ?? env.CASE_API_BEARER_TOKEN;
  if (!bearer) {
    throw new PeerError(
      "UNAUTHORIZED",
      "sentinel_session cookie or CASE_API_BEARER_TOKEN required",
      "cfg-case-missing-session",
      401,
    );
  }

  return createRealPeerCaseClient({
    baseUrl,
    bearerToken: bearer,
    fetchImpl: overrides?.fetchImpl,
  });
}
