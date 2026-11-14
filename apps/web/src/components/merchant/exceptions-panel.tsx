"use client";

import { useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createMerchantInboxClientForMode } from "@/adapters/composition-peers";
import type {
  InboxExceptionItem,
  MerchantInboxClient,
} from "@/application/ports";
import { PeerError } from "@/domain/types";
import { formatAmountMinor, maskTransactionRef } from "@/domain/mask";
import type { AuthSession } from "@/lib/server/auth";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";
import { FIXTURE_EXCEPTIONS } from "../../../tests/stubs/merchant-inbox";

type Props = {
  session: AuthSession;
  /** Test override; defaults to mode-wired BFF / fixture client. */
  inboxClient?: MerchantInboxClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty" }
  | {
      status: "ready";
      items: InboxExceptionItem[];
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
    return FIXTURE_EXCEPTIONS[0]!.merchant_ref;
  }
  return null;
}

/**
 * Merchant Exceptions: list via BFF `/api/bff/merchant-inbox`
 * → GET /v1/exceptions?merchant_ref=.
 * Escalation is not resolution. Real-peer failure stays visible.
 */
export function ExceptionsPanel({ session, inboxClient }: Props) {
  const { config } = useShell();
  const client = useMemo(() => {
    if (inboxClient === null) return null;
    if (inboxClient) return inboxClient;
    return createMerchantInboxClientForMode(config.mode);
  }, [inboxClient, config.mode]);

  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!client) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Merchant inbox client not configured",
          });
        }
        return;
      }
      const merchantRef = merchantRefFromSession(session, config.mode);
      if (!merchantRef) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail:
              "Active assignment has no merchant_ref; exceptions withheld",
          });
        }
        return;
      }
      try {
        const { items } = await client.listExceptions({
          merchant_ref: merchantRef,
        });
        if (cancelled) return;
        if (items.length === 0) {
          setLoad({ status: "empty" });
          return;
        }
        setLoad({
          status: "ready",
          items,
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
    <div className="panel stack" data-testid="merchant-exceptions">
      <h1>Exceptions</h1>
      <p className="muted">
        Exception inbox from merchant-inbox{" "}
        <code>GET /v1/exceptions</code>. Escalation is not verified credit.
      </p>
      {config.mode === "fixture" ||
      (load.status === "ready" && load.source === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading exceptions…" />
      ) : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState
            tone="error"
            title="Exceptions unavailable"
            detail={load.detail}
          />
        </div>
      ) : null}
      {load.status === "empty" ? (
        <UiState
          tone="empty"
          title="No exceptions"
          detail="No exception items in merchant scope."
        />
      ) : null}
      {load.status === "ready" ? (
        <table
          className="table"
          aria-label="Merchant exceptions"
          data-testid="merchant-exceptions-list"
        >
          <thead>
            <tr>
              <th>Item</th>
              <th>Kind</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Transaction</th>
            </tr>
          </thead>
          <tbody>
            {load.items.map((row) => (
              <tr key={row.item_id}>
                <td>{row.item_id}</td>
                <td>{row.kind}</td>
                <td className="tnum">
                  {formatAmountMinor(row.amount_minor, row.currency)}
                </td>
                <td>{row.status}</td>
                <td>
                  {row.transaction_ref
                    ? maskTransactionRef(row.transaction_ref)
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
