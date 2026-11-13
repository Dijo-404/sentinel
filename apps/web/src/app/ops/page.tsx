"use client";

import { ShellLayout } from "@/components/shell-layout";
import { OperatorQueue } from "@/components/operator-queue";
import { useShell } from "@/adapters/shell-context";

export default function OpsPage() {
  const { caseClient, config } = useShell();
  return (
    <ShellLayout current="ops" mode={config.mode} voiceEnabled={config.voiceEnabled}>
      <OperatorQueue caseClient={caseClient} />
    </ShellLayout>
  );
}
