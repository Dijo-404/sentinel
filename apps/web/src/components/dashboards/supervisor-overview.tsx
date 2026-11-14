"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useShell } from "@/adapters/shell-context";
import type { CaseClient } from "@/application/ports";
import { PeerError } from "@/domain/types";
import type { AuthSession } from "@/lib/server/auth";
import { PORTAL_META } from "@/lib/permissions";
import { ChartCard } from "@/components/viz/chart-card";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { StatBlock } from "@/components/viz/stat-block";
import { TrendPill } from "@/components/viz/trend-pill";
import { UiState } from "@/components/ui-states";

type Props = {
  session: AuthSession;
  /** Optional override for tests; defaults to shell case client. Explicit null skips shell client. */
  caseClient?: CaseClient | null;
};

export type SupervisorDashboardKpis = {
  waiting_approval_cases: number;
  escalated_cases: number;
  pending_approvals: number;
  label: string;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "permission"; detail: string }
  | { status: "unavailable"; detail: string }
  | {
      status: "ready";
      kpis: SupervisorDashboardKpis;
      source: "live" | "fixture";
    };

export function SupervisorOverview({
  session,
  caseClient: caseClientProp,
}: Props) {
  const { caseClient: shellClient, config } = useShell();
  const caseClient =
    caseClientProp === undefined ? shellClient : caseClientProp;
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [chartReady, setChartReady] = useState(false);

  useEffect(() => {
    setChartReady(true);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadData() {
      setLoad({ status: "loading" });
      if (!caseClient) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "PEER_UNAVAILABLE: Case client unavailable",
          });
        }
        return;
      }
      if (!caseClient.getSupervisorDashboard) {
        if (!cancelled) {
          setLoad({
            status: "unavailable",
            detail: "Supervisor dashboard port not available on this client",
          });
        }
        return;
      }
      try {
        const kpis = await caseClient.getSupervisorDashboard();
        if (cancelled) return;
        setLoad({
          status: "ready",
          kpis,
          source: config.mode === "fixture" ? "fixture" : "live",
        });
      } catch (err) {
        if (cancelled) return;
        if (
          err instanceof PeerError &&
          (err.httpStatus === 403 || err.code === "FORBIDDEN")
        ) {
          setLoad({
            status: "permission",
            detail: `${err.code}: ${err.message}`,
          });
          return;
        }
        const detail =
          err instanceof PeerError
            ? `${err.code}: ${err.message}`
            : err instanceof Error
              ? err.message
              : "Load failed";
        setLoad({ status: "error", detail });
      }
    }
    void loadData();
    return () => {
      cancelled = true;
    };
  }, [caseClient, config.mode]);

  const chartRows = useMemo(() => {
    if (load.status !== "ready") return [];
    return [
      {
        key: "waiting",
        label: "Waiting approval",
        count: load.kpis.waiting_approval_cases,
      },
      {
        key: "escalated",
        label: "Escalated",
        count: load.kpis.escalated_cases,
      },
      {
        key: "pending",
        label: "Pending approvals",
        count: load.kpis.pending_approvals,
      },
    ];
  }, [load]);

  const meta = PORTAL_META.supervisor;
  const showFixtureBanner =
    config.mode === "fixture" ||
    (load.status === "ready" && load.source === "fixture");
  const caption =
    load.status === "ready" && load.source === "live"
      ? "Scoped projection"
      : "Fixture peer";

  return (
    <div className="stack" data-testid="supervisor-dashboard">
      <div className="panel stack">
        <h1>{meta.title} dashboard</h1>
        <p className="muted">{meta.description}</p>
        <p className="muted">
          Signed in as {session.user.email} · {session.assignment.label}
        </p>
        {showFixtureBanner ? <FixtureBanner /> : null}
      </div>

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading supervisor overview…" />
      ) : null}
      {load.status === "permission" ? (
        <UiState
          tone="permission"
          title="Permission denied"
          detail={load.detail}
        />
      ) : null}
      {load.status === "error" ? (
        <UiState
          tone="error"
          title="Overview unavailable"
          detail={load.detail}
        />
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
          <div className="kpi-row" data-testid="supervisor-kpi-row">
            <StatBlock
              label="Waiting approval"
              value={String(load.kpis.waiting_approval_cases)}
              caption={caption}
            />
            <StatBlock
              label="Escalated"
              value={String(load.kpis.escalated_cases)}
              caption={caption}
            />
            <StatBlock
              label="Pending approvals"
              value={String(load.kpis.pending_approvals)}
              caption={caption}
            />
            <div
              className="stack"
              style={{ gap: "0.5rem", justifyContent: "center" }}
            >
              <TrendPill
                value={
                  load.kpis.waiting_approval_cases > 0
                    ? "Queue active"
                    : "Queue clear"
                }
                direction={
                  load.kpis.waiting_approval_cases > 0 ? "up" : "flat"
                }
              />
              <p className="muted" data-testid="supervisor-projection-label">
                {load.kpis.label}
              </p>
              <Link
                href="/supervisor/approvals"
                data-testid="supervisor-open-approvals"
              >
                Open approvals
              </Link>
            </div>
          </div>

          <ChartCard title="Dashboard projection">
            <div
              style={{ width: "100%", height: 220 }}
              data-testid="supervisor-projection-chart"
            >
              {chartReady ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={chartRows}
                    margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
                  >
                    <XAxis
                      dataKey="label"
                      tick={{ fill: "var(--fog)", fontSize: 11 }}
                      interval={0}
                      angle={-20}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fill: "var(--fog)", fontSize: 11 }}
                      width={28}
                    />
                    <Tooltip />
                    <Bar
                      dataKey="count"
                      fill="var(--periwinkle)"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : null}
            </div>
          </ChartCard>
        </>
      ) : null}
    </div>
  );
}
