import type { CaseClient } from "@/application/ports";
import { createRealPeerCaseClient } from "./real-peer-case-client";

/**
 * Browser case client for portal users.
 * Calls same-origin BFF (`/api/bff/case/...`); the route attaches the
 * httpOnly sentinel_session bearer. No shared process-wide token.
 */
export function createBffCaseClient(options?: {
  fetchImpl?: typeof fetch;
}): CaseClient {
  return createRealPeerCaseClient({
    baseUrl: "/api/bff/case",
    ledgerBaseUrl: "/api/bff/ledger",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
