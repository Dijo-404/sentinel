import type { ApprovalSlotProps } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { demoAction } from "../case-api";
import caseDemo from "../../../contracts/fixtures/case-demo.json";
import evidenceBundle from "../../../contracts/fixtures/evidence-bundle.json";
import type { Case, Evidence } from "@/domain/types";

export type StubApprovalUi = "valid" | "unavailable" | "malformed" | "unauthorized_or_out_of_scope";

export type ApprovalUiStubResult =
  | { status: "ok"; props: ApprovalSlotProps }
  | { status: "error"; error: PeerError }
  | { status: "malformed"; props: unknown };

/**
 * Local approval-ui.v1 double. Supplies slot props or explicit failure.
 * Fixture mode uses LocalApprovalSubstitute; real-peers mounts SN-013 ApprovalPanel.
 */
export function createApprovalUiStub(
  scenario: StubApprovalUi = "valid",
  decide: ApprovalSlotProps["decide"] = async () => {
    throw new PeerError("NOT_WIRED", "decide not wired", "req-approve-stub");
  },
): ApprovalUiStubResult {
  if (scenario === "unavailable") {
    return {
      status: "error",
      error: new PeerError(
        "PEER_UNAVAILABLE",
        "approval-ui peer unavailable",
        "req-approval-unavailable",
        503,
      ),
    };
  }
  if (scenario === "unauthorized_or_out_of_scope") {
    return {
      status: "error",
      error: new PeerError("FORBIDDEN", "approval-ui out of scope", "req-approval-forbidden", 403),
    };
  }
  if (scenario === "malformed") {
    return {
      status: "malformed",
      props: { caseRecord: null, action: { status: "???" }, evidence: "x" },
    };
  }
  return {
    status: "ok",
    props: {
      caseRecord: caseDemo as Case,
      action: demoAction,
      evidence: (evidenceBundle as { evidence: Evidence[] }).evidence,
      decisionExpiresAt: "2026-12-31T23:59:59Z",
      decide,
    },
  };
}

export const APPROVAL_UI_SCENARIOS: StubApprovalUi[] = [
  "valid",
  "unavailable",
  "malformed",
  "unauthorized_or_out_of_scope",
];
