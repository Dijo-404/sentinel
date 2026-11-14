"use client";

import { use } from "react";
import { EvidencePanel } from "@/components/evidence-panel";
import { useShell } from "@/adapters/shell-context";

export default function OperatorCaseEvidencePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = use(params);
  const { caseClient } = useShell();
  return <EvidencePanel caseId={caseId} caseClient={caseClient} />;
}
