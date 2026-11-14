"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { CaseClient, ShellMode } from "@/application/ports";
import type { Case, CaseState } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { labelCaseStatus } from "@/domain/status-labels";
import type { AuthSession } from "@/lib/server/auth";
import { PORTAL_META } from "@/lib/permissions";
import { ChartCard } from "@/components/viz/chart-card";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { fixtureSeries } from "@/components/viz/fixture-series";
import { StatBlock } from "@/components/viz/stat-block";
import { UiState } from "@/components/ui-states";

type Props = {
  session: AuthSession;
  caseClient: CaseClient;
  mode?: ShellMode;
};

type Kpis = {
  open: number;
  waiting: number;
  /** null when cases lack due times — never splice fixture overdue into case rows. */
  overdue: number | null;
  interventions: number;
  source: "cases" | "fixture";
};

type StatusSlice = { name: string; value: number };

const TERMINAL: ReadonlySet<CaseState> = new Set([
  "VERIFIED_RESOLVED",
  "CLOSED_NO_ACTION",
]);

const WAITING: ReadonlySet<CaseState> = new Set([
  "WAITING_APPROVAL",
  "WAITING_EXTERNAL",
  "NEEDS_INPUT",
]);

const PIE_COLORS = ["#5266eb", "#9cb4e8", "#c3c3cc", "#edecfb", "#7a86c8"];

const SIMULATOR_CAPTION = "Simulator";

function fixtureKpis(): Kpis {
  const [open, waiting, overdue, interventions] = fixtureSeries.dailySeries(
    4,
    5,
    8,
  );
  return {
    open: open ?? 8,
    waiting: waiting ?? 8,
    overdue: overdue ?? 8,
    interventions: interventions ?? 8,
    source: "fixture",
  };
}

function fixtureStatusSlices(): StatusSlice[] {
  const points = fixtureSeries.labeledSeries(4, 13, 6);
  const names = ["Open", "Waiting", "Overdue", "Escalated"];
  return points.map((p, i) => ({
    name: names[i] ?? p.x,
    value: p.y,
  }));
}

/** Derive open / waiting / interventions from ops cases. Overdue needs due times — fixture only. */
export function deriveOperatorKpis(cases: Case[]): Omit<
  Kpis,
  "overdue" | "source"
> & {
  overdue: number | null;
} {
  let open = 0;
  let waiting = 0;
  let interventions = 0;
  for (const c of cases) {
    if (!TERMINAL.has(c.status)) open += 1;
    if (WAITING.has(c.status)) waiting += 1;
    if (c.status === "ESCALATED") interventions += 1;
  }
  return { open, waiting, interventions, overdue: null };
}

export function statusHistogram(cases: Case[]): StatusSlice[] {
  const counts = new Map<string, number>();
  for (const c of cases) {
    const name = labelCaseStatus(c.status).text;
    counts.set(name, (counts.get(name) ?? 0) + 1);
  }
  return [...counts.entries()].map(([name, value]) => ({ name, value }));
}

export function OperatorOverview({
  session,
  caseClient,
  mode = "fixture",
}: Props) {
  const meta = PORTAL_META.operator;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cases, setCases] = useState<Case[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await caseClient.listOpsCases();
        if (cancelled) return;
        setCases(result.cases);
      } catch (err) {
        if (cancelled) return;
        setCases(null);
        if (err instanceof PeerError) {
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

  const { kpis, slices, chartTitle } = useMemo(() => {
    if (cases !== null) {
      const derived = deriveOperatorKpis(cases);
      return {
        kpis: {
          open: derived.open,
          waiting: derived.waiting,
          interventions: derived.interventions,
          overdue: derived.overdue,
          source: "cases" as const,
        },
        // Empty list → empty chart; never invent fixtureStatusSlices.
        slices: statusHistogram(cases),
        chartTitle: "Case status (scoped queue)",
      };
    }
    const fallback = fixtureKpis();
    return {
      kpis: fallback,
      slices: fixtureStatusSlices(),
      chartTitle: "Case status (simulator)",
    };
  }, [cases]);

  const showFixtureBanner = mode === "fixture" || kpis.source === "fixture";

  if (loading) {
    return (
      <div className="stack" data-testid="operator-dashboard">
        <UiState tone="loading" title="Loading operator overview…" />
      </div>
    );
  }

  if (error && mode === "real-peers") {
    return (
      <div className="stack" data-testid="operator-dashboard">
        <UiState tone="error" title="Overview unavailable" detail={error} />
      </div>
    );
  }

  return (
    <div className="stack" data-testid="operator-dashboard">
      <div className="panel stack">
        <h1>{meta.title} dashboard</h1>
        <p className="muted">{meta.description}</p>
        <p className="muted">
          Signed in as {session.user.email} · {session.assignment.label}
        </p>
        {showFixtureBanner ? <FixtureBanner /> : null}
        {error ? (
          <p className="muted" role="status">
            Peer list unavailable — showing simulator KPIs ({error})
          </p>
        ) : null}
        <p>
          <Link href="/operator/queue">Open full queue</Link>
        </p>
      </div>

      <div
        className="stack"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(11rem, 1fr))",
          gap: "0.85rem",
        }}
      >
        <StatBlock
          label="Open"
          value={String(kpis.open)}
          caption={
            kpis.source === "cases" ? "From scoped cases" : SIMULATOR_CAPTION
          }
        />
        <StatBlock
          label="Waiting"
          value={String(kpis.waiting)}
          caption={
            kpis.source === "cases"
              ? "Needs input / approval / external"
              : SIMULATOR_CAPTION
          }
        />
        <StatBlock
          label="Overdue"
          value={kpis.overdue == null ? "—" : String(kpis.overdue)}
          caption={
            kpis.overdue == null
              ? kpis.source === "cases"
                ? "No due times"
                : SIMULATOR_CAPTION
              : SIMULATOR_CAPTION
          }
        />
        <StatBlock
          label="Interventions"
          value={String(kpis.interventions)}
          caption={kpis.source === "cases" ? "Escalated" : SIMULATOR_CAPTION}
        />
      </div>

      <ChartCard title={chartTitle}>
        <div
          style={{ width: "100%", height: 260 }}
          data-testid="operator-status-chart"
        >
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={slices}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
              >
                {slices.map((slice, i) => (
                  <Cell
                    key={slice.name}
                    fill={PIE_COLORS[i % PIE_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  );
}
