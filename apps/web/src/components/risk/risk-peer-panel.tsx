"use client";

import { useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createRiskClientForMode } from "@/adapters/composition-peers";
import type {
  RiskClient,
  RiskDashboard,
  RiskFinding,
  RiskInvestigation,
  RiskReport,
  RiskRestriction,
} from "@/application/ports";
import { PeerError } from "@/domain/types";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { StatBlock } from "@/components/viz/stat-block";
import { UiState } from "@/components/ui-states";

export type RiskPeerView = "queue" | "holds" | "transactions" | "audit" | "analytics" | "reports";

type Props = {
  view: RiskPeerView;
  /** Test override; defaults to mode-wired BFF / fixture client. */
  riskClient?: RiskClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | {
      status: "ready";
      source: "live" | "fixture";
      payload:
        | { kind: "investigations"; items: RiskInvestigation[] }
        | { kind: "restrictions"; items: RiskRestriction[] }
        | { kind: "findings"; items: RiskFinding[] }
        | { kind: "dashboard"; metrics: RiskDashboard }
        | { kind: "report"; metrics: RiskReport };
    };

const VIEW_COPY: Record<RiskPeerView, { title: string; muted: string; peerPath: string }> = {
  queue: {
    title: "Risk queue",
    muted: "Investigations from risk via BFF. Not payment authority.",
    peerPath: "GET /v1/risk/investigations",
  },
  holds: {
    title: "Holds",
    muted: "Restrictions that block financial actions. Clearance is not ledger approval.",
    peerPath: "GET /v1/risk/restrictions?blocks_financial_actions=true",
  },
  transactions: {
    title: "Transactions",
    muted: "Restrictions with a transaction_ref. Not a payment ledger; not customer credit.",
    peerPath: "GET /v1/risk/restrictions?has_transaction_ref=true",
  },
  audit: {
    title: "Audit",
    muted: "Versioned findings from risk. Evidence labels stay as recorded.",
    peerPath: "GET /v1/risk/findings",
  },
  analytics: {
    title: "Analytics",
    muted: "Risk dashboard aggregates via BFF. Counts only; not payment authority.",
    peerPath: "GET /v1/risk/dashboard",
  },
  reports: {
    title: "Reports",
    muted: "Summary report read model (dashboard + report_kind).",
    peerPath: "GET /v1/risk/reports",
  },
};

/**
 * Risk portal lists/KPIs via same-origin BFF `/api/bff/risk`.
 * Real-peer failure stays visible — never “Not available yet” or silent fixture.
 */
export function RiskPeerPanel({ view, riskClient }: Props) {
  const { config } = useShell();
  const client = useMemo(() => {
    if (riskClient === null) return null;
    if (riskClient) return riskClient;
    return createRiskClientForMode(config.mode);
  }, [riskClient, config.mode]);

  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const copy = VIEW_COPY[view];

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!client) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Risk client not configured",
          });
        }
        return;
      }
      try {
        const source = config.mode === "fixture" ? "fixture" : "live";
        let payload: Extract<LoadState, { status: "ready" }>["payload"];
        switch (view) {
          case "queue": {
            const { investigations } = await client.listInvestigations();
            payload = { kind: "investigations", items: investigations };
            break;
          }
          case "holds": {
            const { restrictions } = await client.listRestrictions({
              blocks_financial_actions: true,
            });
            payload = { kind: "restrictions", items: restrictions };
            break;
          }
          case "transactions": {
            const { restrictions } = await client.listRestrictions({
              has_transaction_ref: true,
            });
            payload = { kind: "restrictions", items: restrictions };
            break;
          }
          case "audit": {
            const { findings } = await client.listFindings();
            payload = { kind: "findings", items: findings };
            break;
          }
          case "analytics": {
            const metrics = await client.getDashboard();
            payload = { kind: "dashboard", metrics };
            break;
          }
          case "reports": {
            const metrics = await client.getReports();
            payload = { kind: "report", metrics };
            break;
          }
        }
        if (cancelled) return;
        setLoad({ status: "ready", source, payload });
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
  }, [client, config.mode, view]);

  const caption =
    load.status === "ready" && load.source === "live" ? copy.peerPath : "Fixture peer";

  return (
    <div className="panel stack" data-testid={`risk-${view}`}>
      <h1>{copy.title}</h1>
      <p className="muted">{copy.muted}</p>
      {config.mode === "fixture" || (load.status === "ready" && load.source === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? <UiState tone="loading" title="Loading risk data…" /> : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState tone="error" title="Risk peer unavailable" detail={load.detail} />
        </div>
      ) : null}
      {load.status === "ready" ? (
        <div data-testid={`risk-${view}-data`}>
          {load.payload.kind === "investigations" ? (
            <InvestigationTable items={load.payload.items} empty="No investigations" />
          ) : null}
          {load.payload.kind === "restrictions" ? (
            <RestrictionTable
              items={load.payload.items}
              empty={
                view === "transactions"
                  ? "No restrictions with transaction_ref"
                  : "No blocking restrictions"
              }
              showTxn={view === "transactions"}
            />
          ) : null}
          {load.payload.kind === "findings" ? (
            <FindingTable items={load.payload.items} empty="No findings" />
          ) : null}
          {load.payload.kind === "dashboard" || load.payload.kind === "report" ? (
            <KpiGrid
              metrics={load.payload.metrics}
              caption={caption}
              reportKind={
                load.payload.kind === "report" ? load.payload.metrics.report_kind : undefined
              }
            />
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function KpiGrid({
  metrics,
  caption,
  reportKind,
}: {
  metrics: RiskDashboard;
  caption: string;
  reportKind?: string;
}) {
  return (
    <div
      className="stack"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(9.5rem, 1fr))",
        gap: "0.85rem",
      }}
    >
      {reportKind ? <StatBlock label="Report kind" value={reportKind} caption={caption} /> : null}
      <StatBlock
        label="Open investigations"
        value={String(metrics.open_investigations)}
        caption={caption}
      />
      <StatBlock
        label="Active restrictions"
        value={String(metrics.active_restrictions)}
        caption={caption}
      />
      <StatBlock
        label="Awaiting evidence"
        value={String(metrics.awaiting_evidence)}
        caption={caption}
      />
      <StatBlock
        label="Blocked actions"
        value={String(metrics.blocked_actions)}
        caption={caption}
      />
    </div>
  );
}

function InvestigationTable({ items, empty }: { items: RiskInvestigation[]; empty: string }) {
  if (items.length === 0) {
    return <UiState tone="empty" title={empty} />;
  }
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Investigation</th>
            <th>Case</th>
            <th>Status</th>
            <th>Reason</th>
            <th>Queue</th>
            <th>Severity</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.investigation_id}>
              <td>{row.investigation_id}</td>
              <td>{row.case_id}</td>
              <td>{row.status}</td>
              <td>{row.reason_code}</td>
              <td>{row.queue_ref}</td>
              <td>{row.severity}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RestrictionTable({
  items,
  empty,
  showTxn,
}: {
  items: RiskRestriction[];
  empty: string;
  showTxn: boolean;
}) {
  if (items.length === 0) {
    return <UiState tone="empty" title={empty} />;
  }
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Restriction</th>
            <th>Case</th>
            <th>Status</th>
            <th>Blocks financial</th>
            {showTxn ? <th>Transaction ref</th> : null}
            <th>Ledger approval</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.restriction_id}>
              <td>{row.restriction_id}</td>
              <td>{row.case_id}</td>
              <td>{row.status}</td>
              <td>{row.blocks_financial_actions ? "yes" : "no"}</td>
              {showTxn ? <td>{row.transaction_ref ?? "—"}</td> : null}
              <td>{row.financial_approval_granted ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FindingTable({ items, empty }: { items: RiskFinding[]; empty: string }) {
  if (items.length === 0) {
    return <UiState tone="empty" title={empty} />;
  }
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Finding</th>
            <th>Investigation</th>
            <th>Classification</th>
            <th>Notes</th>
            <th>Recorded</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row) => (
            <tr key={row.finding_id}>
              <td>{row.finding_id}</td>
              <td>{row.investigation_id}</td>
              <td>{row.classification}</td>
              <td>{row.notes || "—"}</td>
              <td>{row.recorded_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
