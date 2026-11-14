"use client";

import { useEffect, useState } from "react";
import type { PortalRole } from "../../../tests/stubs/identity";
import type { AuthSession } from "@/lib/server/auth";
import { PORTAL_META } from "@/lib/permissions";
import { useShell } from "@/adapters/shell-context";
import { PeerError } from "@/domain/types";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { StatBlock } from "@/components/viz/stat-block";
import { UiState } from "@/components/ui-states";

type Props = {
  role: PortalRole;
  session: AuthSession;
  highlights?: string[];
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
  | { status: "ready"; kpis: CustomerKpis; source: "live" | "fixture" };

/**
 * Role portal dashboard. Uses scoped case-api projections when available
 * (customer). Otherwise shows explicit unavailable — never fake metric numbers.
 */
export function PortalDashboard({ role, session, highlights }: Props) {
  const meta = PORTAL_META[role];
  const { caseClient, config } = useShell();
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (role !== "customer" || !caseClient.getCustomerDashboard) {
        if (!cancelled) {
          setLoad({
            status: "unavailable",
            detail:
              role === "customer"
                ? "Customer dashboard port not available on this client"
                : `No scoped ${role} metrics projection wired in web-shell`,
          });
        }
        return;
      }
      try {
        const kpis = await caseClient.getCustomerDashboard();
        if (cancelled) return;
        setLoad({
          status: "ready",
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
        if (config.mode === "real-peers") {
          setLoad({ status: "unavailable", detail });
          return;
        }
        setLoad({
          status: "unavailable",
          detail: `Peer unavailable — metrics withheld (${detail})`,
        });
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [caseClient, config.mode, role]);

  const items = highlights ?? [
    `Signed in as ${session.user.email}`,
    `Active assignment: ${session.assignment.label}`,
  ];

  return (
    <div className="stack" data-testid={`${role}-dashboard`}>
      <div className="panel stack">
        <h1>{meta.title} dashboard</h1>
        <p className="muted">{meta.description}</p>
        {config.mode === "fixture" || load.status === "ready" ? (
          <FixtureBanner />
        ) : null}
      </div>
      <div className="panel">
        <h2>Session</h2>
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading metrics…" />
      ) : null}
      {load.status === "unavailable" ? (
        <UiState
          tone="empty"
          title="Metrics unavailable"
          detail={load.detail}
        />
      ) : null}
      {load.status === "ready" ? (
        <div
          className="stack"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(11rem, 1fr))",
            gap: "0.85rem",
          }}
          data-testid="portal-kpi-row"
        >
          <StatBlock
            label="Open cases"
            value={String(load.kpis.open_cases)}
            caption={
              load.source === "live" ? "Scoped projection" : "Fixture peer"
            }
          />
          <StatBlock
            label="Needs input"
            value={String(load.kpis.needs_input)}
            caption={
              load.source === "live" ? "Scoped projection" : "Fixture peer"
            }
          />
          <StatBlock
            label="Waiting approval"
            value={String(load.kpis.waiting_approval)}
            caption={
              load.source === "live" ? "Scoped projection" : "Fixture peer"
            }
          />
          <StatBlock
            label="Verified resolved"
            value={String(load.kpis.verified_resolved)}
            caption={
              load.source === "live" ? "Scoped projection" : "Fixture peer"
            }
          />
        </div>
      ) : null}
    </div>
  );
}
