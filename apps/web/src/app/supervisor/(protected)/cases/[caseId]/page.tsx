"use client";

import { use } from "react";
import Link from "next/link";
import { EvidencePanel } from "@/components/evidence-panel";
import { CaseTimeline } from "@/components/case-timeline";
import { useShell } from "@/adapters/shell-context";
import { FIXTURE_DECISION_EXPIRES_AT } from "@/components/approvals/supervisor-decision-workspace";

export default function SupervisorCaseDetailPage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = use(params);
  const { caseClient, config } = useShell();
  return (
    <div className="stack" data-testid="supervisor-case-detail">
      <div className="panel stack">
        <h1>Case review</h1>
        <p className="muted">
          Evidence and timeline with exact approve/reject when a proposal is present.
        </p>
        <Link href="/supervisor/approvals">Back to approvals</Link>
      </div>
      <EvidencePanel
        caseId={caseId}
        caseClient={caseClient}
        enableApproval
        decisionExpiresAt={FIXTURE_DECISION_EXPIRES_AT}
      />
      <CaseTimeline caseId={caseId} caseClient={caseClient} />
      {config.mode === "fixture" ? (
        <p className="fixture-banner" role="status">
          Fixture mode — approval slot uses local substitute
        </p>
      ) : null}
    </div>
  );
}
