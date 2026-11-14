import type {
  InboxExceptionItem,
  MerchantInboxClient,
} from "@/application/ports";
import { PeerError } from "@/domain/types";
import { createPeerJsonFetcher, type PeerJsonOptions } from "./peer-json";

export type MerchantInboxPeerOptions = Omit<PeerJsonOptions, "peerLabel"> & {
  peerLabel?: string;
};

function validateList(
  json: unknown,
  requestId: string,
): { items: InboxExceptionItem[] } {
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
  const items = (json as { items: unknown[] }).items.map((row, i) => {
    if (!row || typeof row !== "object") {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Exception[${i}] is not an object`,
        requestId,
      );
    }
    const o = row as Record<string, unknown>;
    if (
      typeof o.item_id !== "string" ||
      typeof o.merchant_ref !== "string" ||
      typeof o.kind !== "string" ||
      typeof o.status !== "string" ||
      typeof o.tenant_id !== "string" ||
      typeof o.currency !== "string" ||
      typeof o.amount_minor !== "number" ||
      !Number.isInteger(o.amount_minor)
    ) {
      throw new PeerError(
        "MALFORMED_PEER_RESPONSE",
        `Exception[${i}] missing required fields`,
        requestId,
      );
    }
    const out: InboxExceptionItem = {
      item_id: o.item_id,
      tenant_id: o.tenant_id,
      merchant_ref: o.merchant_ref,
      kind: o.kind,
      amount_minor: o.amount_minor,
      currency: o.currency,
      status: o.status,
    };
    if (typeof o.case_id === "string") out.case_id = o.case_id;
    if (typeof o.transaction_ref === "string") {
      out.transaction_ref = o.transaction_ref;
    }
    if (typeof o.assignee === "string") out.assignee = o.assignee;
    return out;
  });
  return { items };
}

export function createRealPeerMerchantInboxClient(
  options: MerchantInboxPeerOptions,
): MerchantInboxClient {
  const request = createPeerJsonFetcher({
    ...options,
    peerLabel: options.peerLabel ?? "merchant-inbox",
  });

  return {
    listExceptions(query) {
      const params = new URLSearchParams();
      if (query?.merchant_ref) params.set("merchant_ref", query.merchant_ref);
      if (query?.kind) params.set("kind", query.kind);
      if (query?.status) params.set("status", query.status);
      const qs = params.toString();
      return request(
        "GET",
        `/v1/exceptions${qs ? `?${qs}` : ""}`,
        validateList,
      );
    },
  };
}

/** Browser path: same-origin BFF with session cookie. */
export function createBffMerchantInboxClient(options?: {
  fetchImpl?: typeof fetch;
}): MerchantInboxClient {
  return createRealPeerMerchantInboxClient({
    baseUrl: "/api/bff/merchant-inbox",
    authMode: "credentials",
    credentials: "same-origin",
    fetchImpl: options?.fetchImpl,
  });
}
