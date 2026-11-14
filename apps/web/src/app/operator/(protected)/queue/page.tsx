"use client";

import { OperatorQueue } from "@/components/operator-queue";
import { useShell } from "@/adapters/shell-context";

export default function OperatorQueuePage() {
  const { caseClient } = useShell();
  return (
    <div data-testid="operator-queue">
      <OperatorQueue caseClient={caseClient} />
    </div>
  );
}
