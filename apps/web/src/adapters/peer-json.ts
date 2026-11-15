import { PeerError, isApiError } from "@/domain/types";
import { newRequestId } from "@/lib/request-id";

export type PeerJsonOptions = {
  baseUrl: string;
  peerLabel: string;
  authMode?: "bearer" | "credentials";
  bearerToken?: string;
  credentials?: RequestCredentials;
  fetchImpl?: typeof fetch;
};

/**
 * Shared JSON peer fetch. Failures stay visible — no fixture fallback.
 */
export function createPeerJsonFetcher(options: PeerJsonOptions) {
  const base = options.baseUrl.replace(/\/$/, "");
  const fetchImpl = options.fetchImpl ?? fetch;
  const authMode = options.authMode ?? "bearer";

  if (!base) {
    throw new PeerError(
      "PEER_UNAVAILABLE",
      `${options.peerLabel} base URL is required`,
      "cfg-missing-base",
      503,
    );
  }
  if (authMode === "bearer" && !options.bearerToken) {
    throw new PeerError(
      "UNAUTHORIZED",
      `Session bearer required for ${options.peerLabel}`,
      "cfg-missing-token",
      401,
    );
  }

  return async function request<T>(
    method: string,
    path: string,
    validate: (json: unknown, requestId: string) => T,
    body?: unknown,
  ): Promise<T> {
    const requestId = `web-${newRequestId()}`;
    let response: Response;
    try {
      const headers: Record<string, string> = {
        ...(authMode === "bearer" ? { Authorization: `Bearer ${options.bearerToken}` } : {}),
        Accept: "application/json",
        "X-Request-Id": requestId,
      };
      if (body !== undefined) {
        headers["Content-Type"] = "application/json";
      }
      response = await fetchImpl(`${base}${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        credentials: options.credentials,
      });
    } catch (err) {
      throw new PeerError(
        "PEER_UNAVAILABLE",
        err instanceof Error ? err.message : `Network failure contacting ${options.peerLabel}`,
        requestId,
        503,
      );
    }

    let json: unknown = undefined;
    const text = await response.text();
    if (text) {
      try {
        json = JSON.parse(text);
      } catch {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          "Peer returned non-JSON body",
          requestId,
          response.status,
        );
      }
    }

    if (!response.ok) {
      if (isApiError(json)) {
        throw new PeerError(json.code, json.message, json.request_id, response.status);
      }
      throw new PeerError(
        response.status === 403 || response.status === 401
          ? "FORBIDDEN"
          : response.status === 503
            ? "PEER_UNAVAILABLE"
            : "PEER_ERROR",
        `${options.peerLabel} returned HTTP ${response.status}`,
        requestId,
        response.status,
      );
    }

    return validate(json, requestId);
  };
}
