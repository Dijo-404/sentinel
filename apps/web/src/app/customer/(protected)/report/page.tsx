"use client";

import { useShell } from "@/adapters/shell-context";
import { IntakeForm } from "@/components/intake-form";

export default function CustomerReportPage() {
  const { caseClient, voiceClient, config } = useShell();
  return (
    <div data-testid="customer-report">
      <IntakeForm
        title="Report an issue"
        caseClient={caseClient}
        voiceEnabled={config.voiceEnabled}
        voiceClient={voiceClient}
      />
    </div>
  );
}
