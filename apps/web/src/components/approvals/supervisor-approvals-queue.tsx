"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { CaseClient } from "@/application/ports";
import type { Case } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { labelCaseStatus } from "@/domain/status-labels";
import { StatusChip } from "@/components/status-chip";
import { UiState } from "@/components/ui-states";
import { MaskedRef } from "@/components/masked-ref";
import { maskReference } from "@/domain/mask";

type Props = {
  caseClient: CaseClient;
  mode: "fixture" | "real-peers";
};

/** Supervisor approval queue — ledger proposals via case-api list projection. */
export function SupervisorApprovalsQueue({ caseClient, mode }: Props) {
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
        const result = await caseClient.listOpsCases({
          status: "WAITING_APPROVAL",
        });
        if (cancelled) return;
        setCases(result.cases);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof PeerError && (err.httpStatus === 403 || err.code === "FORBIDDEN")) {
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

  if (loading) {
    return <UiState tone="loading" title="Loading approval queue…" />;
  }
  if (permission) {
    return <UiState tone="permission" title="Permission denied" detail={permission} />;
  }
  if (error) {
    return <UiState tone="error" title="Approvals unavailable" detail={error} />;
  }

  return (
    <div className="stack" data-testid="supervisor-approvals">
      <div className="panel stack">
        <h1>Approvals</h1>
        <p className="muted">
          Exact digest/revision/expiry decisions. Amounts are not editable here.
        </p>
        {mode === "fixture" ? (
          <p className="fixture-banner" role="status">
            Fixture mode — case-api stub + local approval-ui substitute
          </p>
        ) : (
          <p className="fixture-banner" role="status">
            Real-peer mode — case-api decision proxy; failures stay visible
          </p>
        )}
      </div>
      {cases.length === 0 ? (
        <UiState
          tone="empty"
          title="Queue empty"
          detail="No cases waiting for supervisor approval."
        />
      ) : (
        <div className="panel" style={{ overflowX: "auto" }}>
          <table className="table" aria-label="Pending approvals">
            <thead>
              <tr>
                <th scope="col">Case</th>
                <th scope="col">Status</th>
                <th scope="col">Intent</th>
                <th scope="col">Revision</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => {
                const actionId = c.action_id;
                return (
                  <tr key={c.case_id} data-testid={`approval-row-${c.case_id}`}>
                    <td>
                      <MaskedRef label="case_id" masked={maskReference(c.case_id, "case-…")} />
                    </td>
                    <td>
                      <StatusChip label={labelCaseStatus(c.status)} />
                    </td>
                    <td>{c.intent}</td>
                    <td className="mono">{c.revision}</td>
                    <td>
                      {actionId ? (
                        <Link
                          href={`/supervisor/approvals/${encodeURIComponent(actionId)}`}
                          data-testid={`open-approval-${actionId}`}
                        >
                          Open decision
                        </Link>
                      ) : (
                        <span className="muted">No action</span>
                      )}
                      {" · "}
                      <Link href={`/supervisor/cases/${encodeURIComponent(c.case_id)}`}>Case</Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
