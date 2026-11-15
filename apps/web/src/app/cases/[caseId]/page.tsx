"use client";

import { use } from "react";
import { ShellLayout } from "@/components/shell-layout";
import { CaseTimeline } from "@/components/case-timeline";
import { useShell } from "@/adapters/shell-context";

export default function CasePage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = use(params);
  const { caseClient, config } = useShell();
  return (
    <ShellLayout current="home" mode={config.mode} voiceEnabled={config.voiceEnabled}>
      <CaseTimeline caseId={caseId} caseClient={caseClient} />
    </ShellLayout>
  );
}
