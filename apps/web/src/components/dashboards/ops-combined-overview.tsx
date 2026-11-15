"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useShell } from "@/adapters/shell-context";
import type { CaseClient, ShellMode } from "@/application/ports";
import { PeerError } from "@/domain/types";
import type { AuthSession } from "@/lib/server/auth";
import {
  projectionStatusSlices,
  type OperatorDashboardKpis,
} from "@/components/dashboards/operator-overview";
import type { SupervisorDashboardKpis } from "@/components/dashboards/supervisor-overview";
import { ChartCard } from "@/components/viz/chart-card";
import { ChartTooltip } from "@/components/viz/chart-tooltip";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { StatBlock } from "@/components/viz/stat-block";
import { TrendPill } from "@/components/viz/trend-pill";
import { UiState } from "@/components/ui-states";

type Props = {
  session: AuthSession;
  caseClient?: CaseClient | null;
  mode?: ShellMode;
};

type PartialLoad<T> =
  | { status: "hidden" }
  | { status: "ready"; data: T; source: "live" | "fixture" }
  | { status: "unavailable"; detail: string }
  | { status: "permission"; detail: string };

type CombinedState =
  | { status: "loading" }
  | {
      status: "ready";
      operator: PartialLoad<OperatorDashboardKpis>;
      supervisor: PartialLoad<SupervisorDashboardKpis>;
    };

/** Overlapping status counts (one case can be assigned and waiting), so bars, not a part-of-whole donut. */
function CountBars({ data }: { data: { label: string; count: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <XAxis
          dataKey="label"
          tick={{ fill: "var(--ink-secondary)", fontSize: 12 }}
          tickLine={false}
          interval={0}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fill: "var(--ink-secondary)", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={28}
        />
        <Tooltip cursor={{ fill: "rgba(82, 102, 235, 0.06)" }} content={<ChartTooltip />} />
        <Bar
          dataKey="count"
          name="Cases"
          fill="var(--periwinkle)"
          radius={[4, 4, 0, 0]}
          maxBarSize={72}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

function peerDetail(err: unknown): string {
  if (err instanceof PeerError) return `${err.code}: ${err.message}`;
  if (err instanceof Error) return err.message;
  return "Load failed";
}

async function loadOperator(
  client: CaseClient,
  mode: ShellMode,
): Promise<PartialLoad<OperatorDashboardKpis>> {
  if (!client.getOperatorDashboard) {
    return {
      status: "unavailable",
      detail: "Operator dashboard port not available on this client",
    };
  }
  try {
    const data = await client.getOperatorDashboard();
    return {
      status: "ready",
      data,
      source: mode === "fixture" ? "fixture" : "live",
    };
  } catch (err) {
    if (err instanceof PeerError && (err.httpStatus === 403 || err.code === "FORBIDDEN")) {
      return { status: "permission", detail: peerDetail(err) };
    }
    return { status: "unavailable", detail: peerDetail(err) };
  }
}

async function loadSupervisor(
  client: CaseClient,
  mode: ShellMode,
): Promise<PartialLoad<SupervisorDashboardKpis>> {
  if (!client.getSupervisorDashboard) {
    return {
      status: "unavailable",
      detail: "Supervisor dashboard port not available on this client",
    };
  }
  try {
    const data = await client.getSupervisorDashboard();
    return {
      status: "ready",
      data,
      source: mode === "fixture" ? "fixture" : "live",
    };
  } catch (err) {
    if (err instanceof PeerError && (err.httpStatus === 403 || err.code === "FORBIDDEN")) {
      return { status: "permission", detail: peerDetail(err) };
    }
    return { status: "unavailable", detail: peerDetail(err) };
  }
}

/**
 * Combined operator + supervisor projections for the shared ops workspace.
 * Partial peer failure keeps the other role's section visible.
 */
export function OpsCombinedOverview({
  session,
  caseClient: caseClientProp,
  mode: modeProp,
}: Props) {
  const { caseClient: shellClient, config } = useShell();
  const caseClient = caseClientProp === undefined ? shellClient : caseClientProp;
  const mode = modeProp ?? config.mode;
  const [load, setLoad] = useState<CombinedState>({ status: "loading" });
  const [chartReady, setChartReady] = useState(false);

  useEffect(() => {
    setChartReady(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoad({ status: "loading" });
      if (!caseClient) {
        if (!cancelled) {
          setLoad({
            status: "ready",
            operator: {
              status: "unavailable",
              detail: "PEER_UNAVAILABLE: Case client unavailable",
            },
            supervisor: {
              status: "unavailable",
              detail: "PEER_UNAVAILABLE: Case client unavailable",
            },
          });
        }
        return;
      }
      const [operator, supervisor] = await Promise.all([
        session.assignment.role === "operator"
          ? loadOperator(caseClient, mode)
          : Promise.resolve({ status: "hidden" } as const),
        session.assignment.role === "supervisor"
          ? loadSupervisor(caseClient, mode)
          : Promise.resolve({ status: "hidden" } as const),
      ]);
      if (cancelled) return;
      setLoad({ status: "ready", operator, supervisor });
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [caseClient, mode, session.assignment.role]);

  const supervisorBars = useMemo(() => {
    if (load.status !== "ready" || load.supervisor.status !== "ready") {
      return [];
    }
    const kpis = load.supervisor.data;
    return [
      {
        key: "waiting",
        label: "Waiting approval",
        count: kpis.waiting_approval_cases,
      },
      { key: "escalated", label: "Escalated", count: kpis.escalated_cases },
      {
        key: "pending",
        label: "Pending approvals",
        count: kpis.pending_approvals,
      },
    ];
  }, [load]);

  const showFixture =
    mode === "fixture" ||
    (load.status === "ready" &&
      ((load.operator.status === "ready" && load.operator.source === "fixture") ||
        (load.supervisor.status === "ready" && load.supervisor.source === "fixture")));

  return (
    <div className="stack" data-testid="ops-combined-dashboard">
      <div className="panel stack">
        <h1>Operations dashboard</h1>
        <p className="muted">Workload and approval projections for your active role.</p>
        <p className="muted">
          Signed in as {session.user.email} · {session.assignment.label}
        </p>
        {showFixture ? <FixtureBanner /> : null}
        <p>
          <Link href="/operator/queue">Open queue</Link>
          {" · "}
          <Link href="/supervisor/approvals">Open approvals</Link>
        </p>
      </div>

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading operations overview…" />
      ) : null}

      {load.status === "ready" ? (
        <>
          {session.assignment.role === "operator" ? (
            <section className="stack" data-testid="ops-operator-section">
              <h2>Operator workload</h2>
              {load.operator.status === "permission" ? (
                <UiState
                  tone="permission"
                  title="Operator metrics denied"
                  detail={load.operator.detail}
                />
              ) : null}
              {load.operator.status === "unavailable" ? (
                <UiState
                  tone="empty"
                  title="Operator metrics unavailable"
                  detail={load.operator.detail}
                />
              ) : null}
              {load.operator.status === "ready" ? (
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
                      value={String(load.operator.data.open_total)}
                      caption={
                        load.operator.source === "live" ? "Scoped projection" : "Fixture peer"
                      }
                    />
                    <StatBlock
                      label="Waiting"
                      value={String(load.operator.data.waiting_approval)}
                      caption="Cases in WAITING_APPROVAL"
                    />
                    <StatBlock
                      label="Assigned"
                      value={String(load.operator.data.assigned_to_me)}
                      caption={
                        load.operator.source === "live" ? "Scoped projection" : "Fixture peer"
                      }
                    />
                    <StatBlock
                      label="Interventions"
                      value={String(load.operator.data.escalated)}
                      caption={
                        load.operator.source === "live" ? "Scoped projection" : "Fixture peer"
                      }
                    />
                  </div>
                  <ChartCard title="Case status (operator projection)">
                    <div style={{ width: "100%", height: 220 }} data-testid="operator-status-chart">
                      {chartReady ? (
                        <CountBars
                          data={projectionStatusSlices(load.operator.data).map((slice) => ({
                            label: slice.name,
                            count: slice.value,
                          }))}
                        />
                      ) : null}
                    </div>
                  </ChartCard>
                </>
              ) : null}
            </section>
          ) : null}

          {session.assignment.role === "supervisor" ? (
            <section className="stack" data-testid="ops-supervisor-section">
              <h2>Supervisor approvals</h2>
              {load.supervisor.status === "permission" ? (
                <UiState
                  tone="permission"
                  title="Supervisor metrics denied"
                  detail={load.supervisor.detail}
                />
              ) : null}
              {load.supervisor.status === "unavailable" ? (
                <UiState
                  tone="empty"
                  title="Supervisor metrics unavailable"
                  detail={load.supervisor.detail}
                />
              ) : null}
              {load.supervisor.status === "ready" ? (
                <>
                  <div className="kpi-row" data-testid="supervisor-kpi-row">
                    <StatBlock
                      label="Waiting approval"
                      value={String(load.supervisor.data.waiting_approval_cases)}
                      caption="Cases in WAITING_APPROVAL"
                    />
                    <StatBlock
                      label="Escalated"
                      value={String(load.supervisor.data.escalated_cases)}
                      caption={
                        load.supervisor.source === "live" ? "Scoped projection" : "Fixture peer"
                      }
                    />
                    <StatBlock
                      label="Pending approvals"
                      value={String(load.supervisor.data.pending_approvals)}
                      caption="Ledger pending proposals (0 until ledger count wired)"
                    />
                  </div>
                  <div className="row">
                    <TrendPill
                      value={
                        load.supervisor.data.waiting_approval_cases > 0
                          ? "Queue active"
                          : "Queue clear"
                      }
                      direction={load.supervisor.data.waiting_approval_cases > 0 ? "up" : "flat"}
                    />
                    <p className="muted" data-testid="supervisor-projection-label">
                      {load.supervisor.data.label}
                    </p>
                    <Link href="/supervisor/approvals" data-testid="supervisor-open-approvals">
                      Open approvals
                    </Link>
                  </div>
                  <ChartCard title="Approval projection">
                    <div
                      style={{ width: "100%", height: 220 }}
                      data-testid="supervisor-projection-chart"
                    >
                      {chartReady ? <CountBars data={supervisorBars} /> : null}
                    </div>
                  </ChartCard>
                </>
              ) : null}
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
