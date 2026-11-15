import type { InboxExceptionItem, MerchantInboxClient } from "@/application/ports";
import { PeerError } from "@/domain/types";

export const FIXTURE_EXCEPTIONS: InboxExceptionItem[] = [
  {
    item_id: "exc-paid-unfulfilled-1",
    tenant_id: "tenant-demo",
    merchant_ref: "merchant-demo",
    kind: "PAID_UNFULFILLED",
    amount_minor: 250000,
    currency: "INR",
    status: "OPEN",
    case_id: "case-demo-42",
    transaction_ref: "txn-demo-1001",
  },
  {
    item_id: "exc-unmatched-1",
    tenant_id: "tenant-demo",
    merchant_ref: "merchant-demo",
    kind: "UNMATCHED_PAYMENT",
    amount_minor: 9900,
    currency: "INR",
    status: "ASSIGNED",
    assignee: "ops-merchant-1",
    transaction_ref: "txn-demo-1002",
  },
];

export type InboxStub = "valid" | "unavailable" | "empty";

export function createMerchantInboxStub(scenario: InboxStub = "valid"): MerchantInboxClient {
  if (scenario === "unavailable") {
    return {
      async listExceptions() {
        throw new PeerError(
          "PEER_UNAVAILABLE",
          "merchant-inbox peer unavailable",
          "req-mi-unavailable",
          503,
        );
      },
    };
  }
  if (scenario === "empty") {
    return {
      async listExceptions() {
        return { items: [] };
      },
    };
  }
  return {
    async listExceptions(query) {
      let items = FIXTURE_EXCEPTIONS.map((i) => ({ ...i }));
      if (query?.merchant_ref) {
        items = items.map((i) => ({
          ...i,
          merchant_ref: query.merchant_ref!,
        }));
      }
      if (query?.kind) {
        items = items.filter((i) => i.kind === query.kind);
      }
      if (query?.status) {
        items = items.filter((i) => i.status === query.status);
      }
      return { items };
    },
  };
}
