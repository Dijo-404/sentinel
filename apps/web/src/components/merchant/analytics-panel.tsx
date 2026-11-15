"use client";

import { useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createMerchantAnalyticsClientForMode } from "@/adapters/composition-peers";
import type { MerchantAnalyticsClient, MerchantMetrics } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { formatAmountMinor } from "@/domain/mask";
import type { AuthSession } from "@/lib/server/auth";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { StatBlock } from "@/components/viz/stat-block";
import { UiState } from "@/components/ui-states";
import { FIXTURE_MERCHANT_METRICS } from "../../../tests/stubs/merchant-analytics";
import { rollingMetricsWindow } from "@/domain/metrics-window";
import { MerchantMetricsViz } from "./metrics-viz";

type Props = {
  session: AuthSession;
  /** Test override; defaults to mode-wired BFF / fixture client. */
  analyticsClient?: MerchantAnalyticsClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "ready"; metrics: MerchantMetrics; source: "live" | "fixture" };

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
    return FIXTURE_MERCHANT_METRICS.merchant_ref;
  }
  return null;
}

/**
 * Merchant Analytics: metrics via same-origin BFF `/api/bff/merchant-analytics`.
 * Real-peer failure stays visible — never “Not available yet” or silent fixture.
 */
export function AnalyticsPanel({ session, analyticsClient }: Props) {
  const { config } = useShell();
  const client = useMemo(() => {
    if (analyticsClient === null) return null;
    if (analyticsClient) return analyticsClient;
    return createMerchantAnalyticsClientForMode(config.mode);
  }, [analyticsClient, config.mode]);

  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!client) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Merchant analytics client not configured",
          });
        }
        return;
      }
      const merchantRef = merchantRefFromSession(session, config.mode);
      if (!merchantRef) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Active assignment has no merchant_ref; metrics withheld",
          });
        }
        return;
      }
      const window = rollingMetricsWindow();
      try {
        const metrics = await client.getMetrics(merchantRef, window);
        if (cancelled) return;
        setLoad({
          status: "ready",
          metrics,
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

  const caption =
    load.status === "ready" && load.source === "live"
      ? "merchant-analytics projection"
      : "Fixture peer";

  return (
    <div className="stack" data-testid="merchant-analytics">
      <h1>Analytics</h1>
      <p className="muted">
        Merchant metrics from merchant-analytics via BFF. Not payment authority.
      </p>
      {config.mode === "fixture" || (load.status === "ready" && load.source === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading merchant metrics…" />
      ) : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState tone="error" title="Analytics unavailable" detail={load.detail} />
        </div>
      ) : null}
      {load.status === "ready" ? (
        <div
          className="stack"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 12rem), 1fr))",
            gap: "0.85rem",
          }}
          data-testid="merchant-analytics-metrics"
        >
          <StatBlock
            label="Unresolved"
            value={formatAmountMinor(load.metrics.unresolved_minor, load.metrics.currency)}
            caption={caption}
          />
          <StatBlock label="Exception rate" value={load.metrics.exception_rate} caption={caption} />
          <StatBlock
            label="Median handling"
            value={`${load.metrics.median_handling_seconds}s`}
            caption={caption}
          />
          <StatBlock
            label="Top cause"
            value={load.metrics.top_causes[0]?.replace(/_/g, " ").toLowerCase() ?? "—"}
            caption={caption}
          />
        </div>
      ) : null}
      {load.status === "ready" ? <MerchantMetricsViz m={load.metrics} /> : null}
    </div>
  );
}
