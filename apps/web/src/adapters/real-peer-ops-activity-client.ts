import type { ActivityItem, OpsActivityClient } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type OpsActivityPeerOptions = Omit<PeerJsonOptions, "peerLabel"> & {
  peerLabel?: string;
};

function validateActivity(
  json: unknown,
  requestId: string,
): { items: ActivityItem[]; source: string } {
  if (
    !json ||
    typeof json !== "object" ||
    !Array.isArray((json as { items?: unknown }).items)
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Missing items array",
      requestId,
    );
  }
  const body = json as { items: unknown[]; source?: unknown };
  const source =
    typeof body.source === "string" && body.source.trim()
      ? body.source.trim()
      : "live";

  const items = body.items.map((row, i) => {
    if (!row || typeof row !== "object") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Activity[${i}] is not an object`,
        requestId,
      );
    }
    const o = row as Record<string, unknown>;
    if (
      typeof o.activity_id !== "string" ||
      typeof o.kind !== "string" ||
      typeof o.summary !== "string" ||
      typeof o.occurred_at !== "string"
    ) {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Activity[${i}] missing required fields`,
        requestId,
      );
    }
    const out: ActivityItem = {
      activity_id: o.activity_id,
      kind: o.kind,
      summary: o.summary,
      occurred_at: o.occurred_at,
    };
    if (typeof o.case_id === "string") out.case_id = o.case_id;
    return out;
  });

  return { items, source };
}

export function createRealPeerOpsActivityClient(
  options: OpsActivityPeerOptions,
): OpsActivityClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "ops-activity",
  });

  return {
    listActivity() {
      return request("GET", "/v1/activity", validateActivity);
    },
  };
}

/** Browser path: same-origin BFF with session cookie. */
export function createBffOpsActivityClient(options?: {
  fetchImpl?: typeof fetch;
}): OpsActivityClient {
  return createRealPeerOpsActivityClient({
    baseUrl: "/api/bff/ops-activity",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
