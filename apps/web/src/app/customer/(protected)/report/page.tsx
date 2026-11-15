"use client";

import { useShell } from "@/adapters/shell-context";
import { SANDBOX_ORDER_REFS } from "@/adapters/sandbox-paytm-catalog";
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
        orderSuggestions={SANDBOX_ORDER_REFS}
      />
    </div>
  );
}
