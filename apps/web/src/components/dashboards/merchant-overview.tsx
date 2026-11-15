"use client";

import { useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createMerchantAnalyticsClientForMode } from "@/adapters/composition-peers";
import type { MerchantAnalyticsClient, MerchantMetrics } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { formatMoney } from "@/components/ledger/money";
import { humanDuration, parseRate } from "@/components/merchant/metrics-viz";
import type { AuthSession } from "@/lib/server/auth";
import { PORTAL_META } from "@/lib/permissions";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { DashboardHeader } from "./dashboard-header";
import { StatBlock } from "@/components/viz/stat-block";
import { UiState } from "@/components/ui-states";
import { FIXTURE_MERCHANT_METRICS } from "../../../tests/stubs/merchant-analytics";
import { rollingMetricsWindow } from "@/domain/metrics-window";

type Props = {
  session: AuthSession;
  /** Test override; defaults to mode-wired merchant-analytics client. */
  analyticsClient?: MerchantAnalyticsClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "unavailable"; detail: string }
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
  // Fixture-only labeled default. Real-peers never invent a merchant identity.
  if (mode === "fixture") {
    return FIXTURE_MERCHANT_METRICS.merchant_ref;
  }
  return null;
}

/**
 * Merchant dashboard KPIs from merchant-analytics.v1 when available.
 * Real-peer failure stays visible — never silent fixture fill.
 */
export function MerchantOverview({ session, analyticsClient }: Props) {
  const meta = PORTAL_META.merchant;
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
            status: "unavailable",
            detail: "Merchant analytics client not configured",
          });
        }
        return;
      }
      const merchantRef = merchantRefFromSession(session, config.mode);
      if (!merchantRef) {
        if (!cancelled) {
          setLoad({
            status: "unavailable",
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
        setLoad({ status: "unavailable", detail });
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

  const exceptionRate = load.status === "ready" ? parseRate(load.metrics.exception_rate) : null;

  return (
    <div className="stack" data-testid="merchant-dashboard">
      <DashboardHeader
        title={`${meta.title} dashboard`}
        description={meta.description}
        displayName={session.user.display_name}
        workspace={session.assignment.label}
      />
      {config.mode === "fixture" || (load.status === "ready" && load.source === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading merchant metrics…" />
      ) : null}
      {load.status === "unavailable" ? (
        <UiState tone="empty" title="Merchant metrics unavailable" detail={load.detail} />
      ) : null}
      {load.status === "ready" ? (
        <div className="kpi-row" data-testid="merchant-kpi-row">
          <StatBlock
            label="Unresolved"
            value={formatMoney(load.metrics.unresolved_minor, load.metrics.currency)}
            caption={caption}
          />
          <StatBlock
            label="Exception rate"
            value={exceptionRate === null ? "Unavailable" : `${(exceptionRate * 100).toFixed(1)}%`}
            caption={caption}
          />
          <StatBlock
            label="Median handling"
            value={humanDuration(load.metrics.median_handling_seconds)}
            caption={caption}
          />
          <StatBlock
            label="Top cause"
            valueType="text"
            value={load.metrics.top_causes[0]?.replace(/_/g, " ").toLowerCase() ?? "—"}
            caption={caption}
          />
        </div>
      ) : null}
    </div>
  );
}
