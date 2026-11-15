"use client";

import { SupervisorDecisionWorkspace } from "@/components/approvals/supervisor-decision-workspace";
import { useShell } from "@/adapters/shell-context";

export function DecisionView({
  actionId,
  canDecide,
  reviewerId,
}: {
  actionId: string;
  canDecide: boolean;
  /** Authenticated session user id — never shell fixture principal. */
  reviewerId: string;
}) {
  const { caseClient, config } = useShell();
  return (
    <SupervisorDecisionWorkspace
      actionId={actionId}
      caseClient={caseClient}
      mode={config.mode}
      reviewerId={reviewerId}
      canDecide={canDecide}
    />
  );
}
