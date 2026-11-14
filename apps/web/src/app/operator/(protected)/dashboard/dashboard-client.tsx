"use client";

import { OperatorOverview } from "@/components/dashboards/operator-overview";
import { useShell } from "@/adapters/shell-context";
import type { AuthSession } from "@/lib/server/auth";

type Props = {
  session: AuthSession;
};

export function OperatorDashboardClient({ session }: Props) {
  const { caseClient, config } = useShell();
  return (
    <OperatorOverview
      session={session}
      caseClient={caseClient}
      mode={config.mode}
    />
  );
}
