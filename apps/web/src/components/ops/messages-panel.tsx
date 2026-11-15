"use client";

import { useEffect, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import type { CaseClient, OpsMessage } from "@/application/ports";
import { PeerError } from "@/domain/types";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

type Props = {
  /** Test override; defaults to ShellProvider case client. */
  caseClient?: CaseClient | null;
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty" }
  | { status: "ready"; messages: OpsMessage[]; source: "live" | "fixture" };

/**
 * Ops message inbox via case-api `listOpsMessages()`.
 * Real-peer failure stays visible — never “Not available yet”.
 */
export function MessagesPanel({ caseClient: caseClientProp }: Props) {
  const { caseClient: shellClient, config } = useShell();
  const caseClient = caseClientProp === undefined ? shellClient : caseClientProp;

  const [load, setLoad] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!caseClient) {
        if (!cancelled) {
          setLoad({
            status: "error",
            detail: "Case client not configured",
          });
        }
        return;
      }
      try {
        const result = await caseClient.listOpsMessages();
        if (cancelled) return;
        if (result.messages.length === 0) {
          setLoad({ status: "empty" });
          return;
        }
        setLoad({
          status: "ready",
          messages: result.messages,
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
    <div className="panel stack" data-testid="operator-messages">
      <h1>Messages</h1>
      <p className="muted">
        Ops message inbox from case-api <code>GET /v1/ops/messages</code>.
      </p>
      {config.mode === "fixture" || (load.status === "ready" && load.source === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {load.status === "loading" ? <UiState tone="loading" title="Loading messages…" /> : null}
      {load.status === "error" ? (
        <div data-testid="peer-error">
          <UiState tone="error" title="Messages unavailable" detail={load.detail} />
        </div>
      ) : null}
      {load.status === "empty" ? (
        <UiState tone="empty" title="No messages" detail="Message inbox is empty." />
      ) : null}
      {load.status === "ready" ? (
        <div className="panel" style={{ overflowX: "auto" }} data-testid="operator-messages-list">
          <table className="table" aria-label="Ops messages">
            <thead>
              <tr>
                <th scope="col">Case</th>
                <th scope="col">Message</th>
                <th scope="col">Occurred</th>
              </tr>
            </thead>
            <tbody>
              {load.messages.map((m) => (
                <tr key={m.message_id}>
                  <td className="mono">{m.case_id}</td>
                  <td>{m.text}</td>
                  <td className="mono">{m.occurred_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
