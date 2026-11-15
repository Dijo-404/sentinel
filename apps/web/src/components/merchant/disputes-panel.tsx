"use client";

import { useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createMerchantDisputesClientForMode } from "@/adapters/composition-peers";
import type { DisputeCaseSummary, MerchantDisputesClient } from "@/application/ports";
import { PeerError } from "@/domain/types";
import type { AuthSession } from "@/lib/server/auth";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";
import { FIXTURE_DISPUTES } from "../../../tests/stubs/merchant-disputes";

type Props = {
  session: AuthSession;
  /** Test override; defaults to mode-wired BFF / fixture client. */
  disputesClient?: MerchantDisputesClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty" }
  | {
      status: "ready";
      disputes: DisputeCaseSummary[];
      source: "live" | "fixture";
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
    return FIXTURE_DISPUTES[0]!.merchant_ref;
  }
  return null;
}

/**
 * Merchant Disputes: list via BFF `/api/bff/merchant-disputes`
 * → GET /v1/merchants/{merchant_ref}/disputes.
 * Real-peer failure stays visible — never “Not available yet”.
 */
export function DisputesPanel({ session, disputesClient }: Props) {
  const { config } = useShell();
  const client = useMemo(() => {
    if (disputesClient === null) return null;
    if (disputesClient) return disputesClient;
    return createMerchantDisputesClientForMode(config.mode);
  }, [disputesClient, config.mode]);

  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!client) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Merchant disputes client not configured",
          });
        }
        return;
      }
      const merchantRef = merchantRefFromSession(session, config.mode);
      if (!merchantRef) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Active assignment has no merchant_ref; disputes withheld",
          });
        }
        return;
      }
      try {
        const { disputes } = await client.listDisputes(merchantRef);
        if (cancelled) return;
        if (disputes.length === 0) {
          setLoad({ status: "empty" });
          return;
        }
        setLoad({
          status: "ready",
          disputes,
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
  }, [client, config.mode, session]);

  return (
    <div className="panel stack" data-testid="merchant-disputes">
      <h1>Disputes</h1>
      <p className="muted">
        Dispute cases from merchant-disputes{" "}
        <code>GET /v1/merchants/&#123;merchant_ref&#125;/disputes</code>. Not payment authority.
      </p>
      {config.mode === "fixture" || (load.status === "ready" && load.source === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? <UiState tone="loading" title="Loading disputes…" /> : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState tone="error" title="Disputes unavailable" detail={load.detail} />
        </div>
      ) : null}
      {load.status === "empty" ? (
        <UiState tone="empty" title="No disputes" detail="No dispute cases in merchant scope." />
      ) : null}
      {load.status === "ready" ? (
        <table
          className="table"
          aria-label="Merchant disputes"
          data-testid="merchant-disputes-list"
        >
          <thead>
            <tr>
              <th>Dispute</th>
              <th>Case</th>
              <th>Reason</th>
              <th>Deadline</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {load.disputes.map((row) => (
              <tr key={row.dispute_id}>
                <td>{row.dispute_id}</td>
                <td>{row.case_id}</td>
                <td>{row.reason_code}</td>
                <td>{row.deadline_at}</td>
                <td>{row.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}
