"use client";

import { useContext } from "react";
import {
  ApprovalPanel,
  DecisionClientError,
  mapWireError,
  type DecideClient,
} from "sentinel-approval-ui";
import type { ApprovalSlotProps } from "@/application/ports";
import { ShellContext } from "@/adapters/shell-context";
import { PeerError } from "@/domain/types";
import { LocalApprovalSubstitute } from "./local-approval-substitute";

type SlotMode = "fixture" | "real-peers";

type ModeFields = {
  /**
   * Fixture keeps local substitute; real-peers mounts SN-013 ApprovalPanel.
   * Prefer explicit prop. When omitted, inherits ShellProvider config.mode so
   * real-peers cannot silently fall back to LocalApprovalSubstitute.
   */
  mode?: SlotMode;
  /** Authenticated reviewer id for ApprovalPanel view-model (real-peers). */
  reviewerId?: string;
  /** Optional clock for ApprovalPanel evidence/expiry checks (tests). */
  now?: () => Date;
};

type Props =
  | ({ state: "ready"; props: ApprovalSlotProps } & ModeFields)
  | ({ state: "error"; error: PeerError } & ModeFields)
  | ({ state: "malformed" } & ModeFields);

/**
 * Wrap shell CaseClient.decide (BFF / stub) so ApprovalPanel gets DecisionClientError.
 * Money authority stays on case-api; package never holds credentials.
 */
function wrapCaseApiDecide(decide: ApprovalSlotProps["decide"]): DecideClient {
  return async (actionId, request) => {
    try {
      return await decide(actionId, request);
    } catch (err) {
      if (err instanceof PeerError) {
        const status = err.httpStatus ?? 500;
        const wire = {
          code: err.code,
          message: err.message,
          request_id: err.requestId,
        };
        throw new DecisionClientError(status, wire, mapWireError(status, wire));
      }
      throw err;
    }
  };
}

/** Documented approval-ui.v1 slot. Renders local substitute, SN-013 panel, or visible failure. */
export function ApprovalSlot(input: Props) {
  const shell = useContext(ShellContext);
  const mode = input.mode ?? shell?.config.mode ?? "fixture";
  // Real-peers must receive the authenticated reviewer; never invent fixture-${role}.
  const reviewerId =
    input.reviewerId ??
    (mode === "fixture" ? (shell?.config.principal.principal_id ?? "") : "");

  if (input.state === "error") {
    return (
      <section className="slot-box" data-state="error" data-testid="approval-slot" role="alert">
        <h2>Approval slot unavailable</h2>
        <p>
          {input.error.code}: {input.error.message}
        </p>
        <p className="muted">Real-peer failure is visible; fixture fallback is not used.</p>
      </section>
    );
  }
  if (input.state === "malformed") {
    return (
      <section className="slot-box" data-state="error" data-testid="approval-slot" role="alert">
        <h2>Approval slot malformed</h2>
        <p>Peer returned incompatible approval-ui props.</p>
      </section>
    );
  }

  if (mode === "real-peers") {
    const { props } = input;
    return (
      <ApprovalPanel
        case={props.caseRecord}
        action={props.action}
        evidence={props.evidence}
        decisionExpiresAt={props.decisionExpiresAt}
        reviewerId={reviewerId}
        decide={wrapCaseApiDecide(props.decide)}
        now={input.now}
        onRefresh={
          props.onRefresh
            ? () => {
                props.onRefresh?.();
              }
            : undefined
        }
        onConflict={
          props.onConflict
            ? (event) => {
                props.onConflict?.(
                  `${event.reason_code}${event.request_id ? ` (${event.request_id})` : ""}`,
                );
              }
            : undefined
        }
        onDecided={
          props.onRefresh
            ? () => {
                props.onRefresh?.();
              }
            : undefined
        }
      />
    );
  }

  return <LocalApprovalSubstitute {...input.props} />;
}
