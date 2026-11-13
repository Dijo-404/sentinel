"use client";

import type { ApprovalSlotProps } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { LocalApprovalSubstitute } from "./local-approval-substitute";

type Props =
  | { state: "ready"; props: ApprovalSlotProps }
  | { state: "error"; error: PeerError }
  | { state: "malformed" };

/** Documented approval-ui.v1 slot. Renders local substitute or visible failure. */
export function ApprovalSlot(input: Props) {
  if (input.state === "error") {
    return (
      <section
        className="slot-box"
        data-state="error"
        data-testid="approval-slot"
        role="alert"
      >
        <h2>Approval slot unavailable</h2>
        <p>
          {input.error.code}: {input.error.message}
        </p>
        <p className="muted">
          Real-peer failure is visible; fixture fallback is not used.
        </p>
      </section>
    );
  }
  if (input.state === "malformed") {
    return (
      <section
        className="slot-box"
        data-state="error"
        data-testid="approval-slot"
        role="alert"
      >
        <h2>Approval slot malformed</h2>
        <p>Peer returned incompatible approval-ui props.</p>
      </section>
    );
  }
  return <LocalApprovalSubstitute {...input.props} />;
}
