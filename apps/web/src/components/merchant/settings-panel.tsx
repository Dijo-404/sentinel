"use client";

import { useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createMerchantTeamsClientForMode } from "@/adapters/composition-peers";
import type {
  MerchantSettings,
  MerchantTeamsClient,
} from "@/application/ports";
import { PeerError } from "@/domain/types";
import type { AuthSession } from "@/lib/server/auth";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";
import { FIXTURE_MERCHANT_SETTINGS } from "../../../tests/stubs/merchant-teams";

type Props = {
  session: AuthSession;
  /** Test override; defaults to mode-wired BFF / fixture client. */
  teamsClient?: MerchantTeamsClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | {
      status: "ready";
      settings: MerchantSettings;
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
    return FIXTURE_MERCHANT_SETTINGS.merchant_ref;
  }
  return null;
}

/**
 * Merchant Settings: preferences via same-origin BFF `/api/bff/merchant-teams`.
 * Real-peer failure stays visible — never “Not available yet” or silent fixture.
 */
export function SettingsPanel({ session, teamsClient }: Props) {
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
            detail:
              "Active assignment has no merchant_ref; settings withheld",
          });
        }
        return;
      }
      try {
        const settings = await client.getSettings(merchantRef);
        if (cancelled) return;
        setLoad({
          status: "ready",
          settings,
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
    <div className="panel stack" data-testid="merchant-settings">
      <h1>Settings</h1>
      <p className="muted">
        Business preferences from merchant-teams{" "}
        <code>GET /v1/merchant/settings</code>.
      </p>
      {config.mode === "fixture" ||
      (load.status === "ready" && load.label === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? (
        <UiState tone="loading" title="Loading merchant settings…" />
      ) : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState
            tone="error"
            title="Settings unavailable"
            detail={load.detail}
          />
        </div>
      ) : null}
      {load.status === "ready" ? (
        <dl
          className="stack"
          aria-label="Merchant settings"
          data-testid="merchant-settings-data"
        >
          <div>
            <dt className="muted">Merchant</dt>
            <dd>{load.settings.merchant_ref}</dd>
          </div>
          <div>
            <dt className="muted">Notification language</dt>
            <dd>{load.settings.notification_language}</dd>
          </div>
          <div>
            <dt className="muted">Dispute alerts</dt>
            <dd>{load.settings.notify_disputes ? "On" : "Off"}</dd>
          </div>
          <div>
            <dt className="muted">Settlement alerts</dt>
            <dd>{load.settings.notify_settlements ? "On" : "Off"}</dd>
          </div>
        </dl>
      ) : null}
    </div>
  );
}
