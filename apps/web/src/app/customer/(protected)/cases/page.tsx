"use client";

import { useEffect, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import type { CustomerCaseSummary } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { RefundTracker } from "@/components/customer/refund-tracker";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty" }
  | { status: "ready"; cases: CustomerCaseSummary[]; source: "live" | "fixture" };

export default function CustomerCasesPage() {
  const { caseClient, config } = useShell();
  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!caseClient.listCustomerCases) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "listCustomerCases port not available on this client",
          });
        }
        return;
      }
      try {
        const { cases } = await caseClient.listCustomerCases();
        if (cancelled) return;
        if (cases.length === 0) {
          setLoad({ status: "empty" });
          return;
        }
        setLoad({
          status: "ready",
          cases,
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
  }, [caseClient, config.mode]);

  return (
    <div className="stack" data-testid="customer-cases">
      <h1>My refunds</h1>
      <p className="muted">
        Customer-scoped cases from case-api <code>GET /v1/customer/cases</code>.
      </p>
      {config.mode === "fixture" || (load.status === "ready" && load.source === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? <UiState tone="loading" title="Loading cases…" /> : null}
      {load.status === "error" ? (
        <UiState tone="error" title="Cases unavailable" detail={load.detail} />
      ) : null}
      {load.status === "empty" ? (
        <UiState tone="empty" title="No cases" detail="No cases in your subject scope." />
      ) : null}
      {load.status === "ready" ? (
        <div className="tracker-list" aria-label="Customer cases">
          {load.cases.map((row) => (
            <RefundTracker key={row.case_id} row={row} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
