"use client";

import { use } from "react";
import { SupervisorDecisionWorkspace } from "@/components/approvals/supervisor-decision-workspace";
import { useShell } from "@/adapters/shell-context";

export default function SupervisorApprovalDetailPage({
  params,
}: {
  params: Promise<{ actionId: string }>;
}) {
  const { actionId } = use(params);
  const { caseClient, config } = useShell();
  return (
    <SupervisorDecisionWorkspace
      actionId={actionId}
      caseClient={caseClient}
      mode={config.mode}
    />
  );
}
