import type { MerchantSettings, MerchantStaff, MerchantTeamsClient } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type MerchantTeamsPeerOptions = Omit<PeerJsonOptions, "peerLabel"> & {
  peerLabel?: string;
};

function validateSettings(json: unknown, requestId: string): MerchantSettings {
  if (!json || typeof json !== "object") {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Settings response is not an object", requestId);
  }
  const o = json as Record<string, unknown>;
  if (
    typeof o.tenant_id !== "string" ||
    typeof o.merchant_ref !== "string" ||
    typeof o.notification_language !== "string" ||
    typeof o.notify_disputes !== "boolean" ||
    typeof o.notify_settlements !== "boolean"
  ) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Settings missing required fields", requestId);
  }
  return {
    tenant_id: o.tenant_id,
    merchant_ref: o.merchant_ref,
    notification_language: o.notification_language,
    notify_disputes: o.notify_disputes,
    notify_settlements: o.notify_settlements,
  };
}

function validateTeam(
  json: unknown,
  requestId: string,
): {
  staff: MerchantStaff[];
  source: string;
} {
  if (!json || typeof json !== "object" || !Array.isArray((json as { staff?: unknown }).staff)) {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Missing staff array", requestId);
  }
  const body = json as { staff: unknown[]; source?: unknown };
  const source =
    typeof body.source === "string" && body.source.trim() ? body.source.trim() : "local_projection";

  const staff = body.staff.map((row, i) => {
    if (!row || typeof row !== "object") {
      throw new PeerError("MALFORMED_PEER_RESPONSE", `Staff[${i}] is not an object`, requestId);
    }
    const o = row as Record<string, unknown>;
    if (
      typeof o.staff_id !== "string" ||
      typeof o.tenant_id !== "string" ||
      typeof o.merchant_ref !== "string" ||
      typeof o.display_name !== "string" ||
      !Array.isArray(o.roles) ||
      typeof o.active !== "boolean"
    ) {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Staff[${i}] missing required fields`,
        requestId,
      );
    }
    const roles = o.roles.map((r, j) => {
      if (typeof r !== "string") {
        throw new PeerError(
          "MALFORMED_PEER_RESPONSE",
          `Staff[${i}].roles[${j}] is not a string`,
          requestId,
        );
      }
      return r;
    });
    const out: MerchantStaff = {
      staff_id: o.staff_id,
      tenant_id: o.tenant_id,
      merchant_ref: o.merchant_ref,
      display_name: o.display_name,
      roles,
      active: o.active,
    };
    if (typeof o.approval_limit_minor === "number" && Number.isInteger(o.approval_limit_minor)) {
      out.approval_limit_minor = o.approval_limit_minor;
    }
    if (typeof o.currency === "string") out.currency = o.currency;
    return out;
  });

  return { staff, source };
}

export function createRealPeerMerchantTeamsClient(
  options: MerchantTeamsPeerOptions,
): MerchantTeamsClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "merchant-teams",
  });

  return {
    listTeam(merchantRef) {
      const params = new URLSearchParams({ merchant_ref: merchantRef });
      return request("GET", `/v1/merchant/team?${params}`, validateTeam);
    },
    getSettings(merchantRef) {
      const params = new URLSearchParams({ merchant_ref: merchantRef });
      return request("GET", `/v1/merchant/settings?${params}`, validateSettings);
    },
  };
}

/** Browser path: same-origin BFF with session cookie. */
export function createBffMerchantTeamsClient(options?: {
  fetchImpl?: typeof fetch;
}): MerchantTeamsClient {
  return createRealPeerMerchantTeamsClient({
    baseUrl: "/api/bff/merchant-teams",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
