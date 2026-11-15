"use client";

import { useEffect, useMemo, useState } from "react";
import type { PortalRole } from "../../../tests/stubs/identity";
import type { AuthSession } from "@/lib/server/auth";
import { PORTAL_META } from "@/lib/permissions";
import { useShell } from "@/adapters/shell-context";
import { createRiskClientForMode } from "@/adapters/composition-peers";
import type { RiskClient, RiskDashboard } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { DashboardHeader } from "./dashboard-header";
import { StatBlock } from "@/components/viz/stat-block";
import { AdminPeerPanel } from "@/components/admin/admin-peer-panel";
import { UiState } from "@/components/ui-states";

type Props = {
  role: PortalRole;
  session: AuthSession;
  highlights?: string[];
  /** Test override for risk peer. */
  riskClient?: RiskClient | null;
};

type CustomerKpis = {
  open_cases: number;
  needs_input: number;
  waiting_approval: number;
  verified_resolved: number;
};

type LoadState =
  | { status: "loading" }
  | { status: "unavailable"; detail: string }
  | {
      status: "ready";
      kind: "customer";
      kpis: CustomerKpis;
      source: "live" | "fixture";
    }
  | {
      status: "ready";
      kind: "risk";
      kpis: RiskDashboard;
      source: "live" | "fixture";
    };

/**
 * Role portal dashboard. Customer uses case-api projections; risk uses risk.v1.
 * Otherwise explicit unavailable — never fake metric numbers.
 */
export function PortalDashboard({ role, session, highlights, riskClient: riskClientProp }: Props) {
  const meta = PORTAL_META[role];
  const { caseClient, config } = useShell();
  const riskClient = useMemo(() => {
    if (role !== "risk") return null;
    if (riskClientProp === null) return null;
    if (riskClientProp) return riskClientProp;
    return createRiskClientForMode(config.mode);
  }, [role, riskClientProp, config.mode]);
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (role === "customer") {
        if (!caseClient.getCustomerDashboard) {
          if (!cancelled) {
            setLoad({
              status: "unavailable",
              detail: "Customer dashboard port not available on this client",
            });
          }
          return;
        }
        try {
          const kpis = await caseClient.getCustomerDashboard();
          if (cancelled) return;
          setLoad({
            status: "ready",
            kind: "customer",
            kpis,
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
          setLoad({ status: "unavailable", detail });
        }
        return;
      }

      if (role === "risk") {
        if (!riskClient) {
          if (!cancelled) {
            setLoad({
              status: "unavailable",
              detail: "Risk client not configured",
            });
          }
          return;
        }
        try {
          const kpis = await riskClient.getDashboard();
          if (cancelled) return;
          setLoad({
            status: "ready",
            kind: "risk",
            kpis,
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
          setLoad({ status: "unavailable", detail });
        }
        return;
      }

      if (!cancelled) {
        setLoad({
          status: "unavailable",
          detail: `No scoped ${role} metrics projection wired in web-shell`,
        });
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [caseClient, config.mode, role, riskClient]);

  const items = highlights ?? [
    `Signed in as ${session.user.email}`,
    `Active assignment: ${session.assignment.label}`,
  ];

  const caption =
    load.status === "ready" && load.source === "live" ? "Scoped projection" : "Fixture peer";

  return (
    <div className="stack" data-testid={`${role}-dashboard`}>
      <DashboardHeader
        title={`${meta.title} dashboard`}
        description={meta.description}
        displayName={session.user.display_name}
        workspace={session.assignment.label}
      />
      {config.mode === "fixture" || load.status === "ready" ? <FixtureBanner /> : null}
      <details className="panel session-details">
        <summary>Session details</summary>
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </details>

      {load.status === "loading" ? <UiState tone="loading" title="Loading metrics…" /> : null}
      {role === "admin" ? <AdminPeerPanel view="security" headingLevel={2} /> : null}
      {load.status === "unavailable" && role !== "admin" ? (
        <UiState tone="empty" title="Metrics unavailable" detail={load.detail} />
      ) : null}
      {load.status === "ready" && load.kind === "customer" ? (
        <div className="kpi-row" data-testid="portal-kpi-row">
          <StatBlock label="Open cases" value={String(load.kpis.open_cases)} caption={caption} />
          <StatBlock label="Needs input" value={String(load.kpis.needs_input)} caption={caption} />
          <StatBlock
            label="Waiting approval"
            value={String(load.kpis.waiting_approval)}
            caption="Cases in WAITING_APPROVAL"
          />
          <StatBlock
            label="Verified resolved"
            value={String(load.kpis.verified_resolved)}
            caption={caption}
          />
        </div>
      ) : null}
      {load.status === "ready" && load.kind === "risk" ? (
        <div className="kpi-row" data-testid="risk-kpi-row">
          <StatBlock
            label="Open investigations"
            value={String(load.kpis.open_investigations)}
            caption={caption}
          />
          <StatBlock
            label="Active restrictions"
            value={String(load.kpis.active_restrictions)}
            caption={caption}
          />
          <StatBlock
            label="Awaiting evidence"
            value={String(load.kpis.awaiting_evidence)}
            caption={caption}
          />
          <StatBlock
            label="Blocked actions"
            value={String(load.kpis.blocked_actions)}
            caption={caption}
          />
        </div>
      ) : null}
    </div>
  );
}
