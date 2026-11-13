import { describe, expect, it } from "vitest";
import {
  formatAmountMinor,
  maskOrderReference,
  maskProviderRef,
  maskSubjectRef,
  maskTransactionRef,
} from "@/domain/mask";
import {
  labelActionStatus,
  labelCaseStatus,
  labelCredit,
  labelRefundStatus,
} from "@/domain/status-labels";
import { CONTRACT_SHA256 } from "@/domain/types";

describe("masking", () => {
  it("masks payment and subject refs", () => {
    expect(maskTransactionRef("TXN-B")).toBe("txn-…XN-B");
    expect(maskProviderRef("refund-demo-1")).toBe("prov-…mo-1");
    expect(maskSubjectRef("subject-demo-9")).toBe("subj-…mo-9");
    expect(maskOrderReference("DEMO-ORDER-42")).toBe("ord-…R-42");
  });

  it("formats integer minor units", () => {
    expect(formatAmountMinor(150000, "INR")).toBe("INR 1500.00");
  });
});

describe("status labels", () => {
  it("keeps pending/provider/credit/escalation wording exact", () => {
    expect(labelCaseStatus("WAITING_EXTERNAL").text).toBe("Pending external");
    expect(labelCaseStatus("ESCALATED")).toEqual({
      kind: "escalation",
      text: "Escalated",
    });
    expect(labelActionStatus("PENDING")).toEqual({
      kind: "pending",
      text: "Pending",
    });
    expect(labelActionStatus("PROVIDER_CONFIRMED")).toEqual({
      kind: "provider",
      text: "Provider confirmed",
    });
    expect(labelActionStatus("CREDIT_CONFIRMED")).toEqual({
      kind: "credit",
      text: "Credit confirmed",
    });
    expect(labelRefundStatus("PENDING").kind).toBe("pending");
    expect(labelCredit(false).text).toBe("Credit pending");
    expect(labelCredit(true).text).toBe("Credit confirmed");
  });
});

describe("contract pin", () => {
  it("records baseline hash", () => {
    expect(CONTRACT_SHA256).toBe(
      "0db3ba2bba994f10d3060bc7173035360c15ffe23189cea409f7327e23c36feb",
    );
  });
});
