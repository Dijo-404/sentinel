"use client";

import { SupervisorDecisionWorkspace } from "@/components/approvals/supervisor-decision-workspace";
import { useShell } from "@/adapters/shell-context";

export function DecisionView({
  actionId,
  canDecide,
}: {
  actionId: string;
  canDecide: boolean;
}) {
  const { caseClient, config } = useShell();
  return (
    <SupervisorDecisionWorkspace
      actionId={actionId}
      caseClient={caseClient}
      mode={config.mode}
      reviewerId={config.principal.principal_id}
      canDecide={canDecide}
    />
  );
}
