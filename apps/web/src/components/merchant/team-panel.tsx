"use client";

import { useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createMerchantTeamsClientForMode } from "@/adapters/composition-peers";
import type { MerchantStaff, MerchantTeamsClient } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { formatAmountMinor } from "@/domain/mask";
import type { AuthSession } from "@/lib/server/auth";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";
import { FIXTURE_MERCHANT_STAFF } from "../../../tests/stubs/merchant-teams";

type Props = {
  session: AuthSession;
  /** Test override; defaults to mode-wired BFF / fixture client. */
  teamsClient?: MerchantTeamsClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty"; source: string }
  | {
      status: "ready";
      staff: MerchantStaff[];
      source: string;
      label: "live" | "fixture";
    };

function merchantRefFromSession(
  session: AuthSession,
  mode: "fixture" | "real-peers",
): string | null {
  const scope = session.assignment.scope;
  const scoped = scope?.merchant_id ?? scope?.merchant_ref;
  if (typeof scoped === "string" && scoped.trim()) {
    return scoped.trim();
  }
  if (mode === "fixture") {
    return FIXTURE_MERCHANT_STAFF[0]?.merchant_ref ?? "merchant-demo-1";
  }
  return null;
}

/**
 * Merchant Team: membership via same-origin BFF `/api/bff/merchant-teams`.
 * Real-peer failure stays visible — never “Not available yet” or silent fixture.
 */
export function TeamPanel({ session, teamsClient }: Props) {
  const { config } = useShell();
  const client = useMemo(() => {
    if (teamsClient === null) return null;
    if (teamsClient) return teamsClient;
    return createMerchantTeamsClientForMode(config.mode);
  }, [teamsClient, config.mode]);

  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!client) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Merchant teams client not configured",
          });
        }
        return;
      }
      const merchantRef = merchantRefFromSession(session, config.mode);
      if (!merchantRef) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Active assignment has no merchant_ref; team list withheld",
          });
        }
        return;
      }
      try {
        const { staff, source } = await client.listTeam(merchantRef);
        if (cancelled) return;
        if (staff.length === 0) {
          setLoad({ status: "empty", source });
          return;
        }
        setLoad({
          status: "ready",
          staff,
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
  }, [client, config.mode, session]);

  return (
    <div className="panel stack" data-testid="merchant-team">
      <h1>Team</h1>
      <p className="muted">
        Merchant staff from merchant-teams <code>GET /v1/merchant/team</code>. Advisory limits only
        — not payment authority.
      </p>
      {config.mode === "fixture" || (load.status === "ready" && load.label === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? <UiState tone="loading" title="Loading merchant team…" /> : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState tone="error" title="Team unavailable" detail={load.detail} />
        </div>
      ) : null}
      {load.status === "empty" ? (
        <UiState tone="empty" title="No team members" detail="No staff in merchant scope." />
      ) : null}
      {load.status === "ready" ? (
        <div className="table-scroll" role="region" aria-label="Scrollable data table" tabIndex={0}>
          <table className="table" aria-label="Merchant team" data-testid="merchant-team-list">
            <thead>
              <tr>
                <th>Staff</th>
                <th>Name</th>
                <th>Roles</th>
                <th>Status</th>
                <th>Advisory limit</th>
              </tr>
            </thead>
            <tbody>
              {load.staff.map((row) => (
                <tr key={row.staff_id}>
                  <td>{row.staff_id}</td>
                  <td>{row.display_name}</td>
                  <td>{row.roles.join(", ") || "—"}</td>
                  <td>{row.active ? "Active" : "Inactive"}</td>
                  <td className="tnum">
                    {row.approval_limit_minor != null
                      ? formatAmountMinor(row.approval_limit_minor, row.currency ?? "INR")
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
