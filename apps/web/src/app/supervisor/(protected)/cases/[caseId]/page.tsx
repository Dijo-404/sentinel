"use client";

import { use } from "react";
import Link from "next/link";
import { EvidencePanel } from "@/components/evidence-panel";
import { CaseTimeline } from "@/components/case-timeline";
import { useShell } from "@/adapters/shell-context";

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
          Evidence and timeline with exact approve/reject when a proposal is
          present. Proposal comes from getAction — not a fixture digest.
        </p>
        <Link href="/supervisor/approvals">Back to approvals</Link>
      </div>
      <EvidencePanel caseId={caseId} caseClient={caseClient} enableApproval />
      <CaseTimeline caseId={caseId} caseClient={caseClient} />
      {config.mode === "fixture" ? (
        <p className="fixture-banner" role="status">
          Fixture mode — approval slot uses local substitute; action still from
          stub getAction
        </p>
      ) : null}
    </div>
  );
}
