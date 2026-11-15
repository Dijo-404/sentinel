"use client";

import { useState } from "react";
import { ThemeToggle } from "@/components/motion/theme-toggle";
import { CaseReplay } from "@/components/ledger/case-replay";
import { CohortGrid, HoverArea, RingStack, Sparkline, StreamArea } from "@/components/ledger/charts";
import { EvidenceFreshness } from "@/components/ledger/evidence-freshness";
import { HoldButton } from "@/components/ledger/hold-button";
import { LinkGraph, type GraphEdge, type GraphNode } from "@/components/ledger/link-graph";
import { formatMoney } from "@/components/ledger/money";
import { NumberRoll } from "@/components/ledger/number-roll";
import { Sankey } from "@/components/ledger/sankey";
import { StackedBars } from "@/components/ledger/stacked-bars";
import { Treemap } from "@/components/ledger/treemap";
import { useTicker } from "@/components/ledger/use-ticker";
import { Waterfall } from "@/components/ledger/waterfall";
import type { CaseEvent, Evidence } from "@/domain/types";

const SAMPLE_EVENTS: CaseEvent[] = (
  [
    ["RECEIVED", "case.opened"],
    ["INVESTIGATING", "evidence.requested"],
    ["WAITING_APPROVAL", "proposal.ready"],
    ["EXECUTING", "action.dispatched"],
    ["VERIFYING", "provider.pending"],
    ["VERIFIED_RESOLVED", "credit.verified"],
  ] as const
).map(([status, type], i) => ({
  event_id: `sample-${i}`,
  sequence: i + 1,
  case_id: "case-sample",
  case_revision: i + 1,
  type,
  occurred_at: new Date(Date.UTC(2026, 10, 15, 8 + i, 0)).toISOString(),
  payload: { status, evidence_ids: [], reason_code: "SAMPLE" },
}));

const SAMPLE_EVIDENCE = [
  ["ev-1", "ORDER", 6, 72],
  ["ev-2", "PAYMENT", 52, 72],
  ["ev-3", "REFUND", 80, 72],
].map(([id, kind, ageH, windowH]) => {
  const now = Date.UTC(2026, 10, 15, 12);
  return {
    evidence_id: id,
    case_id: "case-sample",
    source: "sample",
    subject_ref: "sub-sample",
    observed_at: new Date(now - (ageH as number) * 3_600_000).toISOString(),
    expires_at: new Date(now - (ageH as number) * 3_600_000 + (windowH as number) * 3_600_000).toISOString(),
    digest: "sha256:sample",
    verification_status: "VERIFIED",
    facts: { kind } as Evidence["facts"],
  } as Evidence;
});

const NODES: GraphNode[] = [
  { id: "a1", label: "cus_••R1", x: 200, y: 170, kind: "account", score: 0.91 },
  { id: "a2", label: "cus_••R2", x: 110, y: 90, kind: "account", score: 0.78 },
  { id: "a3", label: "cus_••R3", x: 300, y: 80, kind: "account", score: 0.42 },
  { id: "d1", label: "dev_••9F", x: 210, y: 60, kind: "device", score: 0 },
  { id: "r1", label: "bank_••41", x: 210, y: 280, kind: "route", score: 0 },
  { id: "a4", label: "cus_••G1", x: 420, y: 220, kind: "account", score: 0.12 },
];
const EDGES: GraphEdge[] = [
  { a: "a1", b: "d1", type: "device" },
  { a: "a2", b: "d1", type: "device" },
  { a: "a3", b: "d1", type: "device" },
  { a: "a1", b: "r1", type: "route" },
  { a: "a4", b: "r1", type: "route" },
  { a: "a1", b: "a2", type: "behaviour" },
];

const inr = (major: number) => formatMoney(major * 100, "INR").replace(/\.00$/, "");

export function DesignGallery() {
  const t = useTicker(1500);
  const [sel, setSel] = useState("a1");
  const [tree, setTree] = useState(0);
  const [approved, setApproved] = useState(false);
  const series = Array.from({ length: 30 }, (_, i) => Math.round(60 + 22 * Math.sin(i / 4) + i));

  return (
    <div className="gallery">
      <header className="gallery__head">
        <div>
          <p className="eyebrow">Sentinel · Night Ledger 2.0</p>
          <h1>Design system</h1>
          <p className="muted">Every primitive on sample data. Nothing on this page comes from a peer or moves money.</p>
        </div>
        <ThemeToggle />
      </header>

      <section className="gallery__grid">
        <article className="pnl pnl--pad gallery__wide">
          <h2 className="eyebrow">Sankey · money flow</h2>
          <Sankey
            label="Sample flow"
            width={760}
            height={240}
            nodes={[
              { id: "rf", label: "Refunds", column: 0, color: "var(--signal)" },
              { id: "di", label: "Disputes", column: 0, color: "var(--tide)" },
              { id: "ap", label: "Approved", column: 1, color: "var(--mist)" },
              { id: "es", label: "Escalated", column: 1, color: "var(--ember)" },
              { id: "ve", label: "Verified", column: 2, color: "var(--verified)" },
              { id: "pe", label: "Pending", column: 2, color: "var(--tide)" },
            ]}
            links={[
              { source: "rf", target: "ap", value: 214 + t, color: "var(--signal)" },
              { source: "di", target: "ap", value: 86, color: "var(--tide)" },
              { source: "di", target: "es", value: 14, color: "var(--ember)" },
              { source: "ap", target: "ve", value: 254 + t, color: "var(--verified)" },
              { source: "ap", target: "pe", value: 46, color: "var(--tide)" },
            ]}
          />
        </article>
        <article className="pnl pnl--pad">
          <h2 className="eyebrow">Number roll · live</h2>
          <div className="display" style={{ fontSize: "2.6rem", fontWeight: 600 }}>
            <NumberRoll value={inr(184920 + t * 137)} />
          </div>
          <Sparkline values={series.slice(-14)} color="var(--ok)" height={40} />
          <h2 className="eyebrow" style={{ marginTop: "1rem" }}>Status</h2>
          <div className="row">
            <span className="status" data-tone="verified">Credit verified</span>
            <span className="status" data-tone="pending">Provider pending</span>
            <span className="status" data-tone="reserved">Reserved</span>
            <span className="status" data-tone="risk">Escalated</span>
            <span className="status">Investigating</span>
          </div>
        </article>
        <article className="pnl pnl--pad gallery__wide">
          <HoverArea
            caption="Sample volume"
            primary={series}
            secondary={series.map((v) => Math.round(v * 0.82))}
            labels={series.map((_, i) => `Nov ${i + 1}`)}
            render={(i) => (
              <>
                <span className="lk-chart__meta">Hover area · Nov {i + 1}</span>
                <span className="lk-chart__value tnum">{series[i]}</span>
              </>
            )}
          />
        </article>
        <article className="pnl pnl--pad">
          <h2 className="eyebrow">Ring stack</h2>
          <RingStack rings={[{ label: "refunds", value: 0.94, color: "var(--ok)" }, { label: "disputes", value: 0.88, color: "var(--signal)" }, { label: "escalations", value: 0.73, color: "var(--ember)" }]} />
          <h2 className="eyebrow">Stream</h2>
          <StreamArea
            colors={["var(--verified)", "var(--tide)", "var(--signal)"]}
            layers={[0, 1.3, 2.4].map((seed, k) => Array.from({ length: 24 }, (_, i) => 12 + 10 * (0.5 + 0.5 * Math.sin((i + t) / 3 + seed)) + k))}
          />
        </article>
        <article className="pnl pnl--pad gallery__wide">
          <h2 className="eyebrow">Stacked bars · legend toggles · table fallback</h2>
          <StackedBars
            caption="Sample refunds by reason"
            lineLabel="refund rate"
            series={[
              { key: "nr", label: "Not received", color: "var(--signal)" },
              { key: "dm", label: "Damaged", color: "var(--tide)" },
              { key: "du", label: "Duplicate", color: "var(--orchid)" },
            ]}
            rows={Array.from({ length: 20 }, (_, i) => ({
              label: `Nov ${i + 1}`,
              values: { nr: 6 + ((i * 3) % 7), dm: 3 + (i % 4), du: 1 + (i % 3) },
              line: 2.4 + Math.sin(i / 4),
            }))}
          />
        </article>
        <article className="pnl pnl--pad">
          <h2 className="eyebrow">Waterfall</h2>
          <Waterfall
            caption="Sample settlement"
            format={(v) => inr(v)}
            steps={[
              { label: "Gross", value: 620000, kind: "total", color: "var(--signal)" },
              { label: "Fees", value: -38000, kind: "delta", color: "var(--fog)" },
              { label: "Refunds", value: -48000, kind: "delta", color: "var(--ember)" },
              { label: "Net", value: 534000, kind: "total", color: "var(--verified)" },
            ]}
          />
        </article>
        <article className="pnl pnl--pad gallery__wide">
          <h2 className="eyebrow">Link graph · keyboard selectable</h2>
          <LinkGraph nodes={NODES} edges={EDGES} selected={sel} threshold={0.7} onSelect={setSel} width={520} height={320} />
        </article>
        <article className="pnl pnl--pad">
          <h2 className="eyebrow">Treemap</h2>
          <Treemap
            selected={tree}
            onSelect={setTree}
            items={[
              { label: "Headphones", value: 98, color: "var(--signal)", display: inr(98000) },
              { label: "Phone cases", value: 41, color: "var(--tide)", display: inr(41000) },
              { label: "Chargers", value: 30, color: "var(--orchid)", display: inr(30000) },
              { label: "Watches", value: 16, color: "var(--ember)", display: inr(16000) },
            ]}
          />
          <h2 className="eyebrow" style={{ marginTop: "1rem" }}>Hold to approve</h2>
          {approved ? (
            <p className="status stamp" data-tone="verified">Approved (sample only)</p>
          ) : (
            <HoldButton label="Hold to approve sample" onCommit={() => setApproved(true)} />
          )}
        </article>
        <article className="pnl pnl--pad gallery__wide">
          <h2 className="eyebrow">Cohorts</h2>
          <CohortGrid
            cols={["W0", "W1", "W2", "W3", "W4", "W5"]}
            rows={Array.from({ length: 5 }, (_, r) => ({
              label: `Sep ${r * 7 + 1}`,
              cells: Array.from({ length: 6 }, (_, w) => (w + r > 5 ? null : w === 0 ? 100 : Math.round(18 * Math.exp(-w / 2.2) + (r % 3)))),
            }))}
          />
        </article>
      </section>

      <CaseReplay events={SAMPLE_EVENTS} />
      <EvidenceFreshness evidence={SAMPLE_EVIDENCE} now={new Date(Date.UTC(2026, 10, 15, 12))} />
    </div>
  );
}
