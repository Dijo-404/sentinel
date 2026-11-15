"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import type { CaseClient, OpsAuditEvent } from "@/application/ports";
import type { Case } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { maskReference } from "@/domain/mask";
import { Sankey, type SankeyLink, type SankeyNode } from "@/components/ledger/sankey";
import { Sparkline } from "@/components/ledger/charts";
import { NumberRoll } from "@/components/ledger/number-roll";
import { utc } from "@/components/ledger/case-replay";
import { UiState } from "@/components/ui-states";
import { STAGE_NAMES, buildCommandModel, hourlyBuckets } from "./command-model";

const POLL_MS = 10_000;

type Snapshot = { cases: Case[]; events: OpsAuditEvent[]; at: Date };

const STAGE_COLORS = ["var(--fog)", "var(--signal)", "var(--periwinkle)", "var(--tide)", "var(--tide)", "var(--verified)"];

/**
 * Live command center over real ops reads (open + history cases, audit feed).
 * Peer failures stay on screen; there is no fixture fallback.
 */
export function CommandCenter({ caseClient: override }: { caseClient?: CaseClient | null }) {
  const { caseClient: shellClient, config } = useShell();
  const caseClient = override === undefined ? shellClient : override;
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const seen = useRef(new Set<string>());

  const load = useCallback(async () => {
    if (!caseClient) {
      setError("PEER_UNAVAILABLE: Case client unavailable");
      return;
    }
    try {
      const [open, history, audit] = await Promise.all([
        caseClient.listOpsCases(),
        caseClient.listOpsCases({ status: "HISTORY" }),
        caseClient.listOpsAuditEvents(),
      ]);
      setSnap({ cases: [...open.cases, ...history.cases], events: audit.events, at: new Date() });
      setError(null);
    } catch (err) {
      setError(err instanceof PeerError ? `${err.code}: ${err.message}` : err instanceof Error ? err.message : "Load failed");
    }
  }, [caseClient]);

  useEffect(() => {
    void load();
    if (paused) return;
    const id = window.setInterval(() => void load(), POLL_MS);
    return () => window.clearInterval(id);
  }, [load, paused]);

  if (!snap && error) return <UiState tone="error" title="Command center unavailable" detail={error} />;
  if (!snap) return <UiState tone="loading" title="Loading command center…" />;

  const m = buildCommandModel(snap.cases);
  const hourly = hourlyBuckets(snap.events, snap.at);
  const events = [...snap.events].sort((a, b) => b.occurred_at.localeCompare(a.occurred_at)).slice(0, 12);
  const fresh = new Set(events.map((e) => `${e.case_id}:${e.sequence}`).filter((k) => !seen.current.has(k)));
  events.forEach((e) => seen.current.add(`${e.case_id}:${e.sequence}`));

  const nodes: SankeyNode[] = STAGE_NAMES.map((name, i) => ({ id: name, label: name, column: Math.min(i, 5), color: STAGE_COLORS[i] }));
  nodes.push({ id: "Escalated", label: "Escalated", column: 2, color: "var(--ember)" }, { id: "Closed", label: "No action", column: 2, color: "var(--fog)" });
  const links: SankeyLink[] = [];
  for (let i = 0; i < STAGE_NAMES.length - 1; i++) {
    if (m.reached[i + 1] > 0) links.push({ source: STAGE_NAMES[i], target: STAGE_NAMES[i + 1], value: m.reached[i + 1], color: STAGE_COLORS[i + 1] });
  }
  if (m.escalated) links.push({ source: "Investigate", target: "Escalated", value: m.escalated, color: "var(--ember)" });
  if (m.closedNoAction) links.push({ source: "Investigate", target: "Closed", value: m.closedNoAction, color: "var(--fog)" });
  // Escalated / closed cases passed intake → investigate too.
  const offPath = m.escalated + m.closedNoAction;
  const intakeOut = links.find((l) => l.source === "Intake");
  if (intakeOut) intakeOut.value += offPath;
  else if (offPath) links.unshift({ source: "Intake", target: "Investigate", value: offPath, color: STAGE_COLORS[1] });

  const kpis = [
    { label: "Cases in view", value: m.total, tone: "var(--ink)" },
    { label: "Awaiting approval", value: m.waitingApproval, tone: "var(--periwinkle)", href: "/supervisor/approvals" },
    { label: "Dispatched · not yet verified", value: m.inFlight, tone: "var(--provider)" },
    { label: "Credit verified", value: m.verified, tone: "var(--ok)" },
    { label: "Escalated", value: m.escalated, tone: "var(--escalation)", href: "/operator/escalations" },
  ];

  return (
    <div className="cc" data-testid="command-center">
      <header className="cc__head">
        <div>
          <p className="eyebrow">Supervisor · live</p>
          <h1>Command center</h1>
        </div>
        <div className="cc__controls">
          <span className="topbar__mode">
            <span className="live-dot" aria-hidden="true" style={{ opacity: paused ? 0.3 : 1 }} />
            {paused ? "paused" : `updated ${utc(snap.at.toISOString()).slice(11)}`}
          </span>
          <button type="button" className="btn btn-glass" onClick={() => setPaused((p) => !p)} aria-pressed={paused}>
            {paused ? "Resume" : "Pause"}
          </button>
        </div>
      </header>

      {error && (
        <p className="state-banner" data-tone="error" role="alert">
          Latest refresh failed — showing data from {utc(snap.at.toISOString())}. {error}
        </p>
      )}
      <p className="fixture-banner" role="status">
        {config.mode === "fixture" ? "Fixture mode — case-api stub" : "Real peers — case-api /v1/ops/cases + /v1/ops/audit-events"}
      </p>

      <section className="cc__kpis" aria-label="Key numbers">
        {kpis.map((k) => {
          const body = (
            <>
              <span>{k.label}</span>
              <strong className="display" style={{ color: k.tone }}>
                <NumberRoll value={String(k.value)} />
              </strong>
            </>
          );
          return k.href ? (
            <Link key={k.label} href={k.href} className="pnl cc__kpi pnl--interactive">
              {body}
            </Link>
          ) : (
            <div key={k.label} className="pnl cc__kpi">
              {body}
            </div>
          );
        })}
      </section>

      <div className="cc__row">
        <section className="pnl pnl--pad cc__flow" aria-label="Case flow">
          <div className="lk-chart__head">
            <h2>Case flow</h2>
            <span className="lk-chart__meta">cases at or past each stage</span>
          </div>
          {m.total === 0 ? (
            <UiState tone="empty" title="No cases yet" detail="The flow fills in as cases arrive." />
          ) : (
            <Sankey nodes={nodes.filter((n) => links.some((l) => l.source === n.id || l.target === n.id))} links={links} label="Cases flowing through the money path" width={860} height={300} />
          )}
        </section>
        <section className="pnl pnl--pad cc__side" aria-label="Activity">
          <h2>Audit events · 24h</h2>
          <strong className="display cc__big tnum">{hourly.reduce((a, b) => a + b, 0)}</strong>
          <Sparkline values={hourly} color="var(--signal)" height={56} />
          <div className="lk-axis">
            <span>−24h</span>
            <span>now</span>
          </div>
          <h2 style={{ marginTop: "0.5rem" }}>Where cases sit now</h2>
          <ul className="cc__stages">
            {STAGE_NAMES.map((n, i) => (
              <li key={n}>
                <span>{n}</span>
                <i style={{ width: `${m.total ? (m.at[i] / m.total) * 100 : 0}%`, background: STAGE_COLORS[i] }} />
                <code className="tnum">{m.at[i]}</code>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="pnl cc__stream" aria-label="Event stream">
        <div className="cc__stream-head">
          <h2>Event stream</h2>
          <span className="lk-chart__meta">financial audit · unsampled</span>
        </div>
        {events.length === 0 ? (
          <UiState tone="empty" title="No audit events" detail="Nothing recorded yet." />
        ) : (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Time (UTC)</th>
                  <th scope="col">Case</th>
                  <th scope="col">Event</th>
                  <th scope="col">Seq</th>
                </tr>
              </thead>
              <tbody aria-live="polite">
                {events.map((e) => (
                  <tr key={`${e.case_id}:${e.sequence}`} className={fresh.has(`${e.case_id}:${e.sequence}`) ? "feed-in" : undefined}>
                    <td className="mono">{utc(e.occurred_at).slice(5, 16)}</td>
                    <td className="mono">{maskReference(e.case_id, "case-…")}</td>
                    <td>{e.type}</td>
                    <td className="mono tnum">{e.sequence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
