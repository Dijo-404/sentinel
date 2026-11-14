"use client";

import { SupervisorApprovalsQueue } from "@/components/approvals/supervisor-approvals-queue";
import { useShell } from "@/adapters/shell-context";

export default function SupervisorApprovalsPage() {
  const { caseClient, config } = useShell();
  return (
    <SupervisorApprovalsQueue caseClient={caseClient} mode={config.mode} />
  );
}
