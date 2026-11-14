"use client";

import { useEffect, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import type { CaseClient, OpsAuditEvent } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

type Props = {
  /** Test override; defaults to ShellProvider case client. */
  caseClient?: CaseClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty" }
  | { status: "ready"; events: OpsAuditEvent[]; source: "live" | "fixture" };

/**
 * Ops audit feed via case-api `listOpsAuditEvents()`.
 * Read-only — no decide controls. Real-peer failure stays visible.
 */
export function AuditPanel({ caseClient: caseClientProp }: Props) {
  const { caseClient: shellClient, config } = useShell();
  const caseClient =
    caseClientProp === undefined ? shellClient : caseClientProp;

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
        const result = await caseClient.listOpsAuditEvents();
        if (cancelled) return;
        if (result.events.length === 0) {
          setLoad({ status: "empty" });
          return;
        }
        setLoad({
          status: "ready",
          events: result.events,
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
    <div className="panel stack" data-testid="supervisor-audit">
      <h1>Audit</h1>
      <p className="muted">
        Ops audit feed from case-api <code>GET /v1/ops/audit-events</code>.
        Read-only — no approval decisions here.
      </p>
      {config.mode === "fixture" ||
      (load.status === "ready" && load.source === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading audit events…" />
      ) : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState
            tone="error"
            title="Audit unavailable"
            detail={load.detail}
          />
        </div>
      ) : null}
      {load.status === "empty" ? (
        <UiState
          tone="empty"
          title="No audit events"
          detail="Audit feed is empty."
        />
      ) : null}
      {load.status === "ready" ? (
        <div
          className="panel"
          style={{ overflowX: "auto" }}
          data-testid="supervisor-audit-list"
        >
          <table className="table" aria-label="Ops audit events">
            <thead>
              <tr>
                <th scope="col">Type</th>
                <th scope="col">Case</th>
                <th scope="col">Occurred</th>
              </tr>
            </thead>
            <tbody>
              {load.events.map((e) => (
                <tr key={`${e.case_id}-${e.sequence}`}>
                  <td className="mono">{e.type}</td>
                  <td className="mono">{e.case_id}</td>
                  <td className="mono">{e.occurred_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
