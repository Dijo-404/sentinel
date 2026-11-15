"use client";

import { ShellLayout } from "@/components/shell-layout";
import { IntakeForm } from "@/components/intake-form";
import { useShell } from "@/adapters/shell-context";

export default function IntakePage() {
  const { caseClient, voiceClient, config } = useShell();
  return (
    <ShellLayout current="intake" mode={config.mode} voiceEnabled={config.voiceEnabled}>
      <IntakeForm
        caseClient={caseClient}
        voiceEnabled={config.voiceEnabled}
        voiceClient={voiceClient}
      />
    </ShellLayout>
  );
}
