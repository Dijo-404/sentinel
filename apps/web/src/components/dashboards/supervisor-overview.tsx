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
import type { CaseState } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { labelCaseStatus } from "@/domain/status-labels";
import type { AuthSession } from "@/lib/server/auth";
import { PORTAL_META } from "@/lib/permissions";
import { ChartCard } from "@/components/viz/chart-card";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { StatBlock } from "@/components/viz/stat-block";
import { TrendPill } from "@/components/viz/trend-pill";
import { UiState } from "@/components/ui-states";

/** Display-only pipeline stages (enums only — not a second ledger). */
const PIPELINE_STATES: CaseState[] = [
  "RECEIVED",
  "INVESTIGATING",
  "WAITING_APPROVAL",
  "EXECUTING",
  "VERIFYING",
  "ESCALATED",
  "VERIFIED_RESOLVED",
];

const FIXTURE_WAITING = 3;

const FIXTURE_PIPELINE: Record<CaseState, number> = {
  RECEIVED: 4,
  NEEDS_INPUT: 2,
  INVESTIGATING: 6,
  RECONCILING: 1,
  PLANNING: 1,
  POLICY_CHECK: 2,
  WAITING_APPROVAL: FIXTURE_WAITING,
  EXECUTING: 2,
  VERIFYING: 1,
  WAITING_EXTERNAL: 1,
  ESCALATED: 1,
  VERIFIED_RESOLVED: 8,
  CLOSED_NO_ACTION: 3,
};

type Props = {
  session: AuthSession;
  /** Optional override for tests; defaults to shell case client. Explicit null skips shell client. */
  caseClient?: CaseClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "permission"; detail: string }
  | {
      status: "ready";
      waitingCount: number;
      pipeline: Record<string, number>;
      source: "live" | "fixture";
    };

function emptyPipeline(): Record<string, number> {
  const out: Record<string, number> = {};
  for (const state of PIPELINE_STATES) out[state] = 0;
  return out;
}

function histogram(statuses: CaseState[]): Record<string, number> {
  const out = emptyPipeline();
  for (const status of statuses) {
    if (status in out) out[status] += 1;
    else out[status] = 1;
  }
  return out;
}

function fixtureReady(): Extract<LoadState, { status: "ready" }> {
  const pipeline = emptyPipeline();
  for (const state of PIPELINE_STATES) {
    pipeline[state] = FIXTURE_PIPELINE[state] ?? 0;
  }
  return {
    status: "ready",
    waitingCount: FIXTURE_WAITING,
    pipeline,
    source: "fixture",
  };
}

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
        // Real-peers: never silent-fill fixture when peer client missing.
        if (config.mode === "real-peers") {
          if (!cancelled) {
            setLoad({
              status: "error",
              detail: "PEER_UNAVAILABLE: Case client unavailable",
            });
          }
          return;
        }
        if (!cancelled) setLoad(fixtureReady());
        return;
      }
      try {
        const [waiting, all] = await Promise.all([
          caseClient.listOpsCases({ status: "WAITING_APPROVAL" }),
          caseClient.listOpsCases(),
        ]);
        if (cancelled) return;
        setLoad({
          status: "ready",
          waitingCount: waiting.cases.length,
          pipeline: histogram(all.cases.map((c) => c.status)),
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
        // Real-peer: never silent-fallback to fixture.
        if (config.mode === "real-peers") {
          const detail =
            err instanceof PeerError
              ? `${err.code}: ${err.message}`
              : err instanceof Error
                ? err.message
                : "Load failed";
          setLoad({ status: "error", detail });
          return;
        }
        setLoad(fixtureReady());
      }
    }
    void loadData();
    return () => {
      cancelled = true;
    };
  }, [caseClient, config.mode]);

  const chartRows = useMemo(() => {
    if (load.status !== "ready") return [];
    return PIPELINE_STATES.map((state) => ({
      state,
      label: labelCaseStatus(state).text,
      count: load.pipeline[state] ?? 0,
    }));
  }, [load]);

  const meta = PORTAL_META.supervisor;
  const showFixtureBanner =
    config.mode === "fixture" ||
    (load.status === "ready" && load.source === "fixture");

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

      {load.status === "ready" ? (
        <>
          <div className="kpi-row" data-testid="supervisor-kpi-row">
            <StatBlock
              label="Waiting approval"
              value={String(load.waitingCount)}
              caption="Exact digest-bound proposals"
            />
            <StatBlock
              label="In pipeline"
              value={String(
                Object.values(load.pipeline).reduce((a, b) => a + b, 0),
              )}
              caption="Visible case states"
            />
            <div
              className="stack"
              style={{ gap: "0.5rem", justifyContent: "center" }}
            >
              <TrendPill
                value={load.waitingCount > 0 ? "Queue active" : "Queue clear"}
                direction={load.waitingCount > 0 ? "up" : "flat"}
              />
              <Link
                href="/supervisor/approvals"
                data-testid="supervisor-open-approvals"
              >
                Open approvals
              </Link>
            </div>
          </div>

          <div className="panel stack">
            <h2>Pipeline</h2>
            <p className="muted">
              Case-state strip only. Approval ≠ credit; amounts stay locked.
            </p>
            <ol className="pipeline-strip" data-testid="supervisor-pipeline">
              {PIPELINE_STATES.map((state) => (
                <li
                  key={state}
                  className="pipeline-strip__item"
                  data-state={state}
                  data-active={
                    state === "WAITING_APPROVAL" && load.waitingCount > 0
                      ? "true"
                      : undefined
                  }
                >
                  <span className="pipeline-strip__count">
                    {load.pipeline[state] ?? 0}
                  </span>
                  <span className="pipeline-strip__label">
                    {labelCaseStatus(state).text}
                  </span>
                </li>
              ))}
            </ol>
          </div>

          <ChartCard title="Case state volume">
            <div style={{ width: "100%", height: 220 }}>
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
