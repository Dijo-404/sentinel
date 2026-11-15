"use client";

import { use } from "react";
import { CaseTimeline } from "@/components/case-timeline";
import { useShell } from "@/adapters/shell-context";

export default function OperatorCasePage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = use(params);
  const { caseClient } = useShell();
  return (
    <div data-testid="operator-case">
      <CaseTimeline caseId={caseId} caseClient={caseClient} enableInteractions />
    </div>
  );
}
