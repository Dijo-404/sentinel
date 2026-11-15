"use client";

import { useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createMerchantSettlementClientForMode } from "@/adapters/composition-peers";
import type { SettlementFinding } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { formatAmountMinor } from "@/domain/mask";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty" }
  | {
      status: "ready";
      findings: SettlementFinding[];
      source: "live" | "fixture";
    };

/**
 * Settlements page: GET /v1/settlements/findings when peer configured.
 * Batch create/list is not a merchant portal list — findings only.
 */
export default function MerchantSettlementsPage() {
  const { config } = useShell();
  const client = useMemo(() => createMerchantSettlementClientForMode(config.mode), [config.mode]);
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        const { findings } = await client.listFindings();
        if (cancelled) return;
        if (findings.length === 0) {
          setLoad({ status: "empty" });
          return;
        }
        setLoad({
          status: "ready",
          findings,
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
        setLoad({ status: "error", detail });
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [client, config.mode]);

  return (
    <div className="panel stack" data-testid="merchant-settlements">
      <h1>Settlements</h1>
      <p className="muted">
        Settlement findings from merchant-settlement <code>GET /v1/settlements/findings</code>. Not
        cash received.
      </p>
      {config.mode === "fixture" || (load.status === "ready" && load.source === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading settlement findings…" />
      ) : null}
      {load.status === "error" ? (
        <UiState tone="error" title="Settlements unavailable" detail={load.detail} />
      ) : null}
      {load.status === "empty" ? (
        <UiState tone="empty" title="No findings" detail="No settlement findings in scope." />
      ) : null}
      {load.status === "ready" ? (
        <table className="table" aria-label="Settlement findings">
          <thead>
            <tr>
              <th>Finding</th>
              <th>Batch</th>
              <th>Status</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {load.findings.map((row) => (
              <tr key={row.finding_id}>
                <td>{row.finding_id}</td>
                <td>{row.batch_id ?? "—"}</td>
                <td>{row.status}</td>
                <td className="tnum">
                  {row.expected_minor != null
                    ? formatAmountMinor(row.expected_minor, row.currency ?? "INR")
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}
