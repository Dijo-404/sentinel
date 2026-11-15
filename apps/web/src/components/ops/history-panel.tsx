"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import type { CaseClient } from "@/application/ports";
import type { Case } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { labelCaseStatus } from "@/domain/status-labels";
import { maskReference } from "@/domain/mask";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { MaskedRef } from "@/components/masked-ref";
import { StatusChip } from "@/components/status-chip";
import { UiState } from "@/components/ui-states";

type Props = {
  /** Test override; defaults to ShellProvider case client. */
  caseClient?: CaseClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty" }
  | { status: "ready"; cases: Case[]; source: "live" | "fixture" };

/**
 * Terminal ops cases via case-api `listOpsCases({ status: "HISTORY" })`.
 * Real-peer failure stays visible — never “Not available yet”.
 */
export function HistoryPanel({ caseClient: caseClientProp }: Props) {
  const { caseClient: shellClient, config } = useShell();
  const caseClient = caseClientProp === undefined ? shellClient : caseClientProp;

  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!caseClient) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Case client not configured",
          });
        }
        return;
      }
      try {
        const result = await caseClient.listOpsCases({ status: "HISTORY" });
        if (cancelled) return;
        if (result.cases.length === 0) {
          setLoad({ status: "empty" });
          return;
        }
        setLoad({
          status: "ready",
          cases: result.cases,
          source: config.mode === "fixture" ? "fixture" : "live",
        });
      } catch (err) {
        if (cancelled) return;
        const detail =
          err instanceof PeerError
            ? `${err.code}: ${err.message}`
            : err instanceof Error
              ? err.message
              : "Load failed";
        setLoad({ status: "error", detail });
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [caseClient, config.mode]);

  return (
    <div className="panel stack" data-testid="supervisor-history">
      <h1>Approval history</h1>
      <p className="muted">
        Terminal cases from case-api <code>GET /v1/ops/cases?status=HISTORY</code>{" "}
        (VERIFIED_RESOLVED | CLOSED_NO_ACTION).
      </p>
      {config.mode === "fixture" || (load.status === "ready" && load.source === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? <UiState tone="loading" title="Loading history…" /> : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState tone="error" title="History unavailable" detail={load.detail} />
        </div>
      ) : null}
      {load.status === "empty" ? (
        <UiState tone="empty" title="No history" detail="No terminal cases in scope." />
      ) : null}
      {load.status === "ready" ? (
        <div className="panel" style={{ overflowX: "auto" }} data-testid="supervisor-history-list">
          <table className="table" aria-label="Case history">
            <thead>
              <tr>
                <th scope="col">Case</th>
                <th scope="col">Status</th>
                <th scope="col">Intent</th>
                <th scope="col">Revision</th>
              </tr>
            </thead>
            <tbody>
              {load.cases.map((c) => (
                <tr key={c.case_id}>
                  <td>
                    <Link
                      href={`/supervisor/cases/${encodeURIComponent(c.case_id)}`}
                      data-testid={`history-link-${c.case_id}`}
                    >
                      <MaskedRef label="case_id" masked={maskReference(c.case_id, "case-…")} />
                    </Link>
                  </td>
                  <td>
                    <StatusChip label={labelCaseStatus(c.status)} />
                  </td>
                  <td>{c.intent}</td>
                  <td className="mono">{c.revision}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
