"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createOpsActivityClientForMode } from "@/adapters/composition-peers";
import type { ActivityItem, OpsActivityClient } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

type Props = {
  /** Test override; defaults to mode-wired BFF / fixture client. */
  activityClient?: OpsActivityClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty"; source: string }
  | {
      status: "ready";
      items: ActivityItem[];
      source: string;
      label: "live" | "fixture";
    };

/**
 * Operator Activity: feed via same-origin BFF `/api/bff/ops-activity`
 * → ops-activity `GET /v1/activity`. Real-peer failure stays visible —
 * never “Not available yet”.
 */
export function ActivityPanel({ activityClient }: Props) {
  const { config } = useShell();
  const client = useMemo(() => {
    if (activityClient === null) return null;
    if (activityClient) return activityClient;
    return createOpsActivityClientForMode(config.mode);
  }, [activityClient, config.mode]);

  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!client) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Ops activity client not configured",
          });
        }
        return;
      }
      try {
        const { items, source } = await client.listActivity();
        if (cancelled) return;
        if (items.length === 0) {
          setLoad({ status: "empty", source });
          return;
        }
        setLoad({
          status: "ready",
          items,
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
    <div className="panel stack" data-testid="operator-activity">
      <h1>Activity</h1>
      <p className="muted">
        Ops feed from ops-activity <code>GET /v1/activity</code>. Advisory only — not payment
        authority.
      </p>
      {config.mode === "fixture" || (load.status === "ready" && load.label === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? <UiState tone="loading" title="Loading activity…" /> : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState tone="error" title="Activity unavailable" detail={load.detail} />
        </div>
      ) : null}
      {load.status === "empty" ? (
        <UiState tone="empty" title="No activity" detail="No feed rows in tenant scope." />
      ) : null}
      {load.status === "ready" ? (
        <div className="table-scroll" role="region" aria-label="Scrollable data table" tabIndex={0}>
          <table className="table" aria-label="Ops activity" data-testid="operator-activity-list">
            <thead>
              <tr>
                <th>Id</th>
                <th>Kind</th>
                <th>Summary</th>
                <th>When</th>
                <th>Case</th>
              </tr>
            </thead>
            <tbody>
              {load.items.map((row) => (
                <tr key={row.activity_id}>
                  <td className="mono">{row.activity_id}</td>
                  <td>{row.kind}</td>
                  <td>{row.summary}</td>
                  <td className="mono">{row.occurred_at}</td>
                  <td>
                    {row.case_id ? (
                      <Link href={`/operator/cases/${row.case_id}`}>{row.case_id}</Link>
                    ) : (
                      "—"
                    )}
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
