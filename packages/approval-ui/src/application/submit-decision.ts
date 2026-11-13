import { DecisionClientError, mapWireError } from "../domain/errors.js";
import {
  buildDecisionRequest,
  decisionWindowExpired,
  hasExpiredEvidence,
} from "../domain/view-model.js";
import type {
  ApprovalViewModel,
  ConflictEvent,
  Decision,
  DecisionOutcome,
  RefreshEvent,
  WireError,
} from "../domain/types.js";
import type { DecideClient } from "./ports.js";

export type SubmitDecisionDeps = {
  decide: DecideClient;
  view: ApprovalViewModel;
  now: Date;
  onRefresh?: (event: RefreshEvent) => void;
  onConflict?: (event: ConflictEvent) => void;
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

export async function submitDecision(
  deps: SubmitDecisionDeps,
  decision: Decision,
): Promise<DecisionOutcome> {
  const { view, now } = deps;

  if (decisionWindowExpired(view.decision_expires_at, now)) {
    const error: WireError = {
      code: "APPROVAL_EXPIRED",
      message: "Decision window has expired",
      request_id: "local-expired",
    };
    return { ok: false, status: 409, error, ui_code: "EXPIRED" };
  }

  if (hasExpiredEvidence(view.evidence_ages)) {
    const error: WireError = {
      code: "EVIDENCE_EXPIRED",
      message: "One or more evidence records are expired",
      request_id: "local-evidence-expired",
    };
    return { ok: false, status: 409, error, ui_code: "EXPIRED" };
  }

  const request = buildDecisionRequest(
    view.action_digest,
    view.case_revision,
    view.policy_version,
    view.decision_expires_at,
    decision,
  );

  try {
    const approval = await deps.decide(view.action_id, request);
    return { ok: true, approval };
  } catch (caught) {
    if (caught instanceof DecisionClientError) {
      if (caught.uiCode === "STALE") {
        deps.onRefresh?.({
          kind: "refresh",
          reason_code: caught.error.code,
          request_id: caught.error.request_id,
        });
      }
      if (caught.uiCode === "CONFLICT") {
        deps.onConflict?.({
          kind: "conflict",
          reason_code: caught.error.code,
          request_id: caught.error.request_id,
          status: caught.status,
        });
      }
      return {
        ok: false,
        status: caught.status,
        error: caught.error,
        ui_code: caught.uiCode,
      };
    }

    if (isWireError(caught)) {
      const uiCode = mapWireError(409, caught);
      return { ok: false, status: 409, error: caught, ui_code: uiCode };
    }

    const error: WireError = {
      code: "UNKNOWN_CLIENT_FAILURE",
      message: caught instanceof Error ? caught.message : "Unknown client failure",
      request_id: "local-unknown",
    };
    return { ok: false, status: 500, error, ui_code: "UNKNOWN" };
  }
}
