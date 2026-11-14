import type { OpsTeamClient, OpsTeamMember } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type OpsTeamPeerOptions = Omit<PeerJsonOptions, "peerLabel"> & {
  peerLabel?: string;
};

function validateOpsTeam(
  json: unknown,
  requestId: string,
): {
  members: OpsTeamMember[];
  source: string;
} {
  if (
    !json ||
    typeof json !== "object" ||
    !Array.isArray((json as { members?: unknown }).members)
  ) {
    throw new PeerError(
      "MALFORMED_PEER_RESPONSE",
      "Missing members array",
      requestId,
    );
  }
  const body = json as { members: unknown[]; source?: unknown };
  const members = body.members.map((row, i) => {
    if (!row || typeof row !== "object") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Member[${i}] is not an object`,
        requestId,
      );
    }
    const o = row as Record<string, unknown>;
    if (
      typeof o.user_id !== "string" ||
      typeof o.email !== "string" ||
      typeof o.display_name !== "string" ||
      typeof o.role !== "string"
    ) {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Member[${i}] missing required fields`,
        requestId,
      );
    }
    return {
      user_id: o.user_id,
      email: o.email,
      display_name: o.display_name,
      role: o.role,
    };
  });
  return { members, source: "identity" };
}

export function createRealPeerOpsTeamClient(
  options: OpsTeamPeerOptions,
): OpsTeamClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "identity",
  });

  return {
    listOpsTeam() {
      return request("GET", "/v1/ops/team", validateOpsTeam);
    },
  };
}

/** Browser path: same-origin BFF with session cookie. */
export function createBffOpsTeamClient(options?: {
  fetchImpl?: typeof fetch;
}): OpsTeamClient {
  return createRealPeerOpsTeamClient({
    baseUrl: "/api/bff/identity",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
