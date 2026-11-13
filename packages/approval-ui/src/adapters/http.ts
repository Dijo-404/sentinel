import { DecisionClientError, mapWireError } from "../domain/errors.js";
import type { WireError } from "../domain/types.js";

export type AuthorizedHttpConfig = {
  baseUrl: string;
  bearerToken: string;
  fetchImpl?: typeof fetch;
};

function isWireError(value: unknown): value is WireError {
  if (!value || typeof value !== "object") {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.code === "string" &&
    typeof record.message === "string" &&
    typeof record.request_id === "string"
  );
}

/**
 * Real-peer HTTP helper. Never falls back to fixtures on failure.
 */
export async function authorizedJson<T>(
  config: AuthorizedHttpConfig,
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  if (!config.baseUrl || !config.bearerToken) {
    throw new DecisionClientError(
      503,
      {
        code: "PEER_UNAVAILABLE",
        message: "Real-peer base URL or bearer token is not configured",
        request_id: "local-config",
      },
      "UNAVAILABLE",
    );
  }

  const fetchImpl = config.fetchImpl ?? fetch;
  const headers: Record<string, string> = {
    Authorization: `Bearer ${config.bearerToken}`,
    Accept: "application/json",
  };
  const init: RequestInit = { method, headers };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetchImpl(new URL(path, config.baseUrl).toString(), init);
  } catch {
    throw new DecisionClientError(
      503,
      {
        code: "PEER_UNAVAILABLE",
        message: "Required peer unavailable",
        request_id: "local-network",
      },
      "UNAVAILABLE",
    );
  }

  let parsed: unknown;
  try {
    parsed = await response.json();
  } catch {
    throw new DecisionClientError(
      response.status || 502,
      {
        code: "MALFORMED_RESPONSE",
        message: "Peer returned non-JSON body",
        request_id: "local-parse",
      },
      "MALFORMED",
    );
  }

  if (!response.ok) {
    const error = isWireError(parsed)
      ? parsed
      : {
          code: "MALFORMED_RESPONSE",
          message: "Peer returned an error without a contract envelope",
          request_id: "local-envelope",
        };
    throw new DecisionClientError(
      response.status,
      error,
      mapWireError(response.status, error),
    );
  }

  return parsed as T;
}
