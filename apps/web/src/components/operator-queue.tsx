"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { CaseClient } from "@/application/ports";
import type { Case } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { labelCaseStatus } from "@/domain/status-labels";
import { StatusChip } from "./status-chip";
import { UiState } from "./ui-states";
import { MaskedRef } from "./masked-ref";
import { maskReference } from "@/domain/mask";

type Props = {
  caseClient: CaseClient;
};

export function OperatorQueue({ caseClient }: Props) {
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState<Case[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [permission, setPermission] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      setPermission(null);
      try {
        const result = await caseClient.listOpsCases();
        if (cancelled) return;
        setCases(result.cases);
      } catch (err) {
        if (cancelled) return;
        if (
          err instanceof PeerError &&
          (err.httpStatus === 403 || err.code === "FORBIDDEN")
        ) {
          setPermission(`${err.code}: ${err.message}`);
        } else if (err instanceof PeerError) {
          setError(`${err.code}: ${err.message}`);
        } else {
          setError(err instanceof Error ? err.message : "Load failed");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [caseClient]);

  if (loading)
    return <UiState tone="loading" title="Loading operator queue…" />;
  if (permission) {
    return (
      <UiState
        tone="permission"
        title="Permission denied"
        detail={permission}
      />
    );
  }
  if (error)
    return <UiState tone="error" title="Queue unavailable" detail={error} />;
  if (cases.length === 0) {
    return (
      <UiState tone="empty" title="Queue empty" detail="No cases in scope." />
    );
  }

  return (
    <div className="stack">
      <h1>Operator queue</h1>
      <p className="muted">
        Tenant-scoped cases. Escalation is a handoff, not resolution.
      </p>
      <div className="panel" style={{ overflowX: "auto" }}>
        <table className="table" aria-label="Operator cases">
          <thead>
            <tr>
              <th scope="col">Case</th>
              <th scope="col">Status</th>
              <th scope="col">Intent</th>
              <th scope="col">Revision</th>
              <th scope="col">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.case_id}>
                <td>
                  <Link href={`/ops/cases/${c.case_id}/evidence`}>
                    <MaskedRef
                      label="case_id"
                      masked={maskReference(c.case_id, "case-…")}
                    />
                  </Link>
                </td>
                <td>
                  <StatusChip label={labelCaseStatus(c.status)} />
                </td>
                <td>{c.intent}</td>
                <td className="mono">{c.revision}</td>
                <td>
                  <Link href={`/ops/cases/${c.case_id}/evidence`}>
                    Open evidence
                  </Link>
                  {" · "}
                  <Link href={`/cases/${c.case_id}`}>Timeline</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
