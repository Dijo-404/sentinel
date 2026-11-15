"use client";

import { useEffect, useState } from "react";
import { PeerError } from "@/domain/types";
import { UiState } from "@/components/ui-states";
import { StatBlock } from "@/components/viz/stat-block";

export type AdminPeerView =
  | "roles"
  | "tenants"
  | "teams"
  | "policies"
  | "security"
  | "integrations"
  | "merchants"
  | "ai"
  | "evaluations"
  | "observability"
  | "audit";

type Props = {
  view: AdminPeerView;
  /** Test override; defaults to browser fetch (BFF cookie session). */
  fetchImpl?: typeof fetch;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "ready"; payload: unknown };

type ViewCopy = {
  title: string;
  muted: string;
  paths: string[];
};

const VIEW_COPY: Record<AdminPeerView, ViewCopy> = {
  roles: {
    title: "Roles catalog",
    muted: "Identity role catalogs via BFF. Not money authority.",
    paths: ["/api/bff/identity/v1/admin/roles"],
  },
  tenants: {
    title: "Tenants",
    muted: "Tenant projections from identity assignments.",
    paths: ["/api/bff/identity/v1/admin/tenants"],
  },
  teams: {
    title: "Teams",
    muted: "Team aggregates from identity assignments.",
    paths: ["/api/bff/identity/v1/admin/teams"],
  },
  security: {
    title: "Security",
    muted: "MFA / session / suspended counts only. No secrets.",
    paths: ["/api/bff/identity/v1/admin/security"],
  },
  audit: {
    title: "Audit",
    muted: "Identity audit events. Distinct from financial audit.",
    paths: ["/api/bff/identity/v1/admin/audit-events"],
  },
  policies: {
    title: "Policies",
    muted: "Versioned policy artifacts. Read-only — not ledger rule edit.",
    paths: ["/api/bff/policy/v1/policies"],
  },
  merchants: {
    title: "Merchants",
    muted: "Merchant catalog from merchant-teams admin list.",
    paths: ["/api/bff/merchant-teams/v1/admin/merchants"],
  },
  integrations: {
    title: "Integrations",
    muted: "Platform-ai integration metadata. money_authority false.",
    paths: ["/api/bff/platform-ai/v1/integrations"],
  },
  ai: {
    title: "AI configuration",
    muted: "Platform-ai config + runs metadata. No money fields.",
    paths: ["/api/bff/platform-ai/v1/config", "/api/bff/platform-ai/v1/runs"],
  },
  evaluations: {
    title: "Evaluations",
    muted: "Eval reports + gated FinHarness/FinBench status. evaluation.v1 authority.",
    paths: ["/api/bff/evals/v1/reports", "/api/bff/admin-fin-gates"],
  },
  observability: {
    title: "Observability",
    muted: "Telemetry signals + gated FinHarness/FinBench. Never financial audit.",
    paths: ["/api/bff/observability/v1/signals", "/api/bff/admin-fin-gates"],
  },
};

async function fetchJson(path: string, fetchImpl: typeof fetch): Promise<unknown> {
  let response: Response;
  try {
    response = await fetchImpl(path, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
  } catch (err) {
    throw new PeerError(
      "PEER_UNAVAILABLE",
      err instanceof Error ? err.message : "Network failure",
      "admin-peer",
      503,
    );
  }
  if (!response.ok) {
    throw new PeerError(
      "PEER_UNAVAILABLE",
      `HTTP ${response.status}`,
      "admin-peer",
      response.status,
    );
  }
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text) as unknown;
  } catch {
    throw new PeerError("MALFORMED_PEER_RESPONSE", "Response is not JSON", "admin-peer", 502);
  }
}

/**
 * Admin remainder pages: BFF → peer list/summary.
 * Real-peer failure stays visible — never “Not available yet”.
 */
export function AdminPeerPanel({ view, fetchImpl }: Props) {
  const copy = VIEW_COPY[view];
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const doFetch = fetchImpl ?? fetch;

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        if (view === "ai") {
          const [config, runs] = await Promise.all(copy.paths.map((p) => fetchJson(p, doFetch)));
          if (cancelled) return;
          setLoad({ status: "ready", payload: { config, runs } });
          return;
        }
        if (view === "evaluations" || view === "observability") {
          const [primary, gates] = await Promise.all(copy.paths.map((p) => fetchJson(p, doFetch)));
          if (cancelled) return;
          setLoad({
            status: "ready",
            payload:
              view === "evaluations" ? { reports: primary, gates } : { signals: primary, gates },
          });
          return;
        }
        const payload = await fetchJson(copy.paths[0], doFetch);
        if (cancelled) return;
        setLoad({ status: "ready", payload });
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
    // view selects static path list; doFetch is inject-or-global fetch
  }, [view, doFetch]);

  return (
    <div className="panel stack" data-testid={`admin-${view}`}>
      <h1>{copy.title}</h1>
      <p className="muted">{copy.muted}</p>

      {load.status === "loading" ? <UiState tone="loading" title="Loading admin data…" /> : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState tone="error" title="Admin peer unavailable" detail={load.detail} />
        </div>
      ) : null}
      {load.status === "ready" ? (
        <div data-testid={`admin-${view}-data`}>
          <AdminPayload view={view} payload={load.payload} />
        </div>
      ) : null}
    </div>
  );
}

function AdminPayload({ view, payload }: { view: AdminPeerView; payload: unknown }) {
  switch (view) {
    case "roles":
      return <RolesBody data={asRecord(payload)} />;
    case "tenants":
      return (
        <SimpleTable
          rows={asArray(asRecord(payload).tenants)}
          empty="No tenants"
          columns={[
            { key: "tenant_id", label: "Tenant" },
            { key: "display_name", label: "Name" },
            { key: "status", label: "Status" },
          ]}
        />
      );
    case "teams":
      return (
        <SimpleTable
          rows={asArray(asRecord(payload).teams)}
          empty="No teams"
          columns={[
            { key: "team_id", label: "Team" },
            { key: "name", label: "Name" },
            { key: "member_count", label: "Members" },
          ]}
        />
      );
    case "security":
      return <SecurityBody data={asRecord(payload)} />;
    case "audit":
      return (
        <SimpleTable
          rows={asArray(asRecord(payload).events)}
          empty="No audit events"
          columns={[
            { key: "event_id", label: "Event" },
            { key: "action", label: "Action" },
            { key: "target_type", label: "Target type" },
            { key: "target_id", label: "Target" },
            { key: "at", label: "At" },
          ]}
        />
      );
    case "policies":
      return (
        <SimpleTable
          rows={asArray(asRecord(payload).policies)}
          empty="No policies"
          columns={[
            { key: "policy_id", label: "Policy" },
            { key: "version", label: "Version" },
            { key: "status", label: "Status" },
            { key: "updated_at", label: "Updated" },
          ]}
        />
      );
    case "merchants":
      return (
        <SimpleTable
          rows={asArray(asRecord(payload).merchants)}
          empty="No merchants"
          columns={[
            { key: "merchant_ref", label: "Merchant" },
            { key: "display_name", label: "Name" },
            { key: "status", label: "Status" },
          ]}
        />
      );
    case "integrations":
      return (
        <SimpleTable
          rows={asArray(asRecord(payload).integrations)}
          empty="No integrations"
          columns={[
            { key: "integration_id", label: "Integration" },
            { key: "name", label: "Name" },
            { key: "status", label: "Status" },
            { key: "updated_at", label: "Updated" },
          ]}
        />
      );
    case "ai":
      return <AiBody data={asRecord(payload)} />;
    case "evaluations":
      return <EvaluationsBody data={asRecord(payload)} />;
    case "observability":
      return <ObservabilityBody data={asRecord(payload)} />;
  }
}

function FinGatesBlock({ gates }: { gates: Record<string, unknown> }) {
  return (
    <div className="stack" data-testid="admin-fin-gates">
      <h2>FinHarness / FinBench</h2>
      <p className="muted">Independently gated (M5/M8). live_stats always null.</p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(9.5rem, 1fr))",
          gap: "0.85rem",
        }}
      >
        <StatBlock label="FinHarness" value={String(gates.finharness ?? "—")} caption="gate" />
        <StatBlock label="FinBench" value={String(gates.finbench ?? "—")} caption="gate" />
      </div>
    </div>
  );
}

function EvaluationsBody({ data }: { data: Record<string, unknown> }) {
  const reportsPayload = asRecord(data.reports);
  const rows = asArray(reportsPayload.reports ?? data.reports);
  return (
    <div className="stack">
      <FinGatesBlock gates={asRecord(data.gates)} />
      <SimpleTable
        rows={rows}
        empty="No reports"
        columns={[
          { key: "run_id", label: "Run" },
          { key: "status", label: "Status" },
          { key: "mode", label: "Mode" },
          { key: "contract_version", label: "Contract" },
        ]}
      />
    </div>
  );
}

function ObservabilityBody({ data }: { data: Record<string, unknown> }) {
  const signalsPayload = asRecord(data.signals);
  const rows = asArray(signalsPayload.signals ?? data.signals);
  return (
    <div className="stack">
      <FinGatesBlock gates={asRecord(data.gates)} />
      <SimpleTable
        rows={rows}
        empty="No signals"
        columns={[
          { key: "signal_id", label: "Signal" },
          { key: "kind", label: "Kind" },
          { key: "name", label: "Name" },
          { key: "recorded_at", label: "Recorded" },
        ]}
      />
    </div>
  );
}

function RolesBody({ data }: { data: Record<string, unknown> }) {
  const groups = [
    { label: "Human roles", items: asStringArray(data.human_roles) },
    {
      label: "Staff invitable",
      items: asStringArray(data.staff_invitable_roles),
    },
    { label: "Service roles", items: asStringArray(data.service_roles) },
  ];
  return (
    <div className="stack">
      {groups.map((g) => (
        <div key={g.label} className="stack">
          <h2>{g.label}</h2>
          {g.items.length === 0 ? (
            <UiState tone="empty" title={`No ${g.label.toLowerCase()}`} />
          ) : (
            <ul>
              {g.items.map((role) => (
                <li key={role} className="mono">
                  {role}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

function SecurityBody({ data }: { data: Record<string, unknown> }) {
  return (
    <div
      className="stack"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(9.5rem, 1fr))",
        gap: "0.85rem",
      }}
    >
      <StatBlock
        label="MFA verified sessions"
        value={String(data.mfa_verified_sessions ?? "—")}
        caption="identity GET /v1/admin/security"
      />
      <StatBlock
        label="Active sessions"
        value={String(data.active_sessions ?? "—")}
        caption="identity GET /v1/admin/security"
      />
      <StatBlock
        label="Suspended users"
        value={String(data.suspended_users ?? "—")}
        caption="identity GET /v1/admin/security"
      />
      <StatBlock
        label="Updated"
        value={String(data.updated_at ?? "—")}
        caption="identity GET /v1/admin/security"
      />
    </div>
  );
}

function AiBody({ data }: { data: Record<string, unknown> }) {
  const config = asRecord(data.config);
  const runsBody = asRecord(data.runs);
  const models = asArray(config.models);
  const runs = asArray(runsBody.runs);
  return (
    <div className="stack">
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(9.5rem, 1fr))",
          gap: "0.85rem",
        }}
      >
        <StatBlock
          label="Kill switch"
          value={config.kill_switch === true ? "on" : "off"}
          caption="platform-ai GET /v1/config"
        />
        <StatBlock
          label="Updated"
          value={String(config.updated_at ?? "—")}
          caption="platform-ai GET /v1/config"
        />
      </div>
      <h2>Models</h2>
      <SimpleTable
        rows={models}
        empty="No models"
        columns={[{ key: "model_id", label: "Model" }]}
      />
      <h2>Runs</h2>
      <SimpleTable
        rows={runs}
        empty="No runs"
        columns={[
          { key: "run_id", label: "Run" },
          { key: "model_id", label: "Model" },
          { key: "status", label: "Status" },
          { key: "started_at", label: "Started" },
        ]}
      />
    </div>
  );
}

function SimpleTable({
  rows,
  empty,
  columns,
}: {
  rows: Record<string, unknown>[];
  empty: string;
  columns: { key: string; label: string }[];
}) {
  if (rows.length === 0) {
    return <UiState tone="empty" title={empty} />;
  }
  return (
    <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={String(row[columns[0]?.key] ?? i)}>
              {columns.map((c) => (
                <td key={c.key} className="mono">
                  {formatCell(row[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return {};
}

function asArray(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) return [];
  return value.filter(
    (row): row is Record<string, unknown> =>
      !!row && typeof row === "object" && !Array.isArray(row),
  );
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === "string");
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  if (typeof value === "boolean") return value ? "yes" : "no";
  return JSON.stringify(value);
}
