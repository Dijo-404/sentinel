"use client";

import { useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createOpsTeamClientForMode } from "@/adapters/composition-peers";
import type { OpsTeamClient, OpsTeamMember } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

type Props = {
  /** Test override; defaults to mode-wired BFF / fixture client. */
  opsTeamClient?: OpsTeamClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty"; source: string }
  | {
      status: "ready";
      members: OpsTeamMember[];
      source: string;
      label: "live" | "fixture";
    };

/**
 * Supervisor Team: ops principals via same-origin BFF `/api/bff/identity`
 * → identity `GET /v1/ops/team`. Real-peer failure stays visible — never invent roster.
 */
export function TeamPanel({ opsTeamClient }: Props) {
  const { config } = useShell();
  const client = useMemo(() => {
    if (opsTeamClient === null) return null;
    if (opsTeamClient) return opsTeamClient;
    return createOpsTeamClientForMode(config.mode);
  }, [opsTeamClient, config.mode]);

  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!client) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Ops team client not configured",
          });
        }
        return;
      }
      try {
        const { members, source } = await client.listOpsTeam();
        if (cancelled) return;
        if (members.length === 0) {
          setLoad({ status: "empty", source });
          return;
        }
        setLoad({
          status: "ready",
          members,
          source,
          label: config.mode === "fixture" ? "fixture" : "live",
        });
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
  }, [client, config.mode]);

  return (
    <div className="panel stack" data-testid="supervisor-team">
      <h1>Team</h1>
      <p className="muted">
        Ops principals from identity{" "}
        <code>GET /v1/ops/team</code> (supervisor-safe tenant roster — not{" "}
        <code>/v1/admin/users</code>).
      </p>
      {config.mode === "fixture" ||
      (load.status === "ready" && load.label === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading ops team…" />
      ) : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState
            tone="error"
            title="Team unavailable"
            detail={load.detail}
          />
        </div>
      ) : null}
      {load.status === "empty" ? (
        <UiState
          tone="empty"
          title="No team members"
          detail="No operator or supervisor assignments in tenant scope."
        />
      ) : null}
      {load.status === "ready" ? (
        <table
          className="table"
          aria-label="Ops team"
          data-testid="supervisor-team-list"
        >
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Name</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {load.members.map((row) => (
              <tr key={`${row.user_id}:${row.role}`}>
                <td className="mono">{row.user_id}</td>
                <td className="mono">{row.email}</td>
                <td>{row.display_name}</td>
                <td>{row.role}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}
