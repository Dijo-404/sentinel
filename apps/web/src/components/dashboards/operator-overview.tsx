"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { CaseClient, ShellMode } from "@/application/ports";
import { PeerError } from "@/domain/types";
import type { AuthSession } from "@/lib/server/auth";
import { PORTAL_META } from "@/lib/permissions";
import { ChartCard } from "@/components/viz/chart-card";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { StatBlock } from "@/components/viz/stat-block";
import { UiState } from "@/components/ui-states";

type Props = {
  session: AuthSession;
  caseClient: CaseClient;
  mode?: ShellMode;
};

export type OperatorDashboardKpis = {
  assigned_to_me: number;
  unassigned: number;
  escalated: number;
  waiting_approval: number;
  open_total: number;
};

type StatusSlice = { name: string; value: number };

type LoadState =
  | { status: "loading" }
  | { status: "unavailable"; detail: string }
  | {
      status: "ready";
      kpis: OperatorDashboardKpis;
      source: "live" | "fixture";
    };

const PIE_COLORS = ["#5266eb", "#9cb4e8", "#c3c3cc", "#edecfb", "#7a86c8"];

/** Pie slices from operator dashboard projection aggregates (not page-scoped lists). */
export function projectionStatusSlices(kpis: OperatorDashboardKpis): StatusSlice[] {
  return [
    { name: "Assigned to me", value: kpis.assigned_to_me },
    { name: "Unassigned", value: kpis.unassigned },
    { name: "Waiting approval", value: kpis.waiting_approval },
    { name: "Escalated", value: kpis.escalated },
  ].filter((s) => s.value > 0);
}

export function OperatorOverview({
  session,
  caseClient,
  mode = "fixture",
}: Props) {
  const meta = PORTAL_META.operator;
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoad({ status: "loading" });
      if (!caseClient.getOperatorDashboard) {
        if (!cancelled) {
          setLoad({
            status: "unavailable",
            detail: "Operator dashboard port not available on this client",
          });
        }
        return;
      }
      try {
        const kpis = await caseClient.getOperatorDashboard();
        if (cancelled) return;
        setLoad({
          status: "ready",
          kpis,
          source: mode === "fixture" ? "fixture" : "live",
        });
      } catch (err) {
        if (cancelled) return;
        const detail =
          err instanceof PeerError
            ? `${err.code}: ${err.message}`
            : err instanceof Error
              ? err.message
              : "Load failed";
        setLoad({ status: "unavailable", detail });
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [caseClient, mode]);

  const caption =
    load.status === "ready" && load.source === "live"
      ? "Scoped projection"
      : "Fixture peer";

  return (
    <div className="stack" data-testid="operator-dashboard">
      <div className="panel stack">
        <h1>{meta.title} dashboard</h1>
        <p className="muted">{meta.description}</p>
        <p className="muted">
          Signed in as {session.user.email} · {session.assignment.label}
        </p>
        {mode === "fixture" ||
        (load.status === "ready" && load.source === "fixture") ? (
          <FixtureBanner />
        ) : null}
        <p>
          <Link href="/operator/queue">Open full queue</Link>
        </p>
      </div>

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading operator overview…" />
      ) : null}
      {load.status === "unavailable" ? (
        <UiState
          tone="empty"
          title="Metrics unavailable"
          detail={load.detail}
        />
      ) : null}

      {load.status === "ready" ? (
        <>
          <div
            className="stack"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(9.5rem, 1fr))",
              gap: "0.85rem",
            }}
            data-testid="operator-kpi-row"
          >
            <StatBlock
              label="Open"
              value={String(load.kpis.open_total)}
              caption={caption}
            />
            <StatBlock
              label="Waiting"
              value={String(load.kpis.waiting_approval)}
              caption="Cases in WAITING_APPROVAL"
            />
            <StatBlock
              label="Assigned"
              value={String(load.kpis.assigned_to_me)}
              caption={caption}
            />
            <StatBlock
              label="Interventions"
              value={String(load.kpis.escalated)}
              caption={caption}
            />
          </div>

          <ChartCard title="Case status (scoped projection)">
            <div
              style={{ width: "100%", height: 260 }}
              data-testid="operator-status-chart"
            >
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={projectionStatusSlices(load.kpis)}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                  >
                    {projectionStatusSlices(load.kpis).map((slice, i) => (
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
        </>
      ) : null}
    </div>
  );
}
