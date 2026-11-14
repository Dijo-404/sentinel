"use client";

import { use } from "react";
import { ShellLayout } from "@/components/shell-layout";
import { EvidencePanel } from "@/components/evidence-panel";
import { useShell } from "@/adapters/shell-context";

export default function EvidencePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = use(params);
  const { caseClient, config } = useShell();
  return (
    <ShellLayout
      current="ops"
      mode={config.mode}
      voiceEnabled={config.voiceEnabled}
    >
      <EvidencePanel caseId={caseId} caseClient={caseClient} />
    </ShellLayout>
  );
}
