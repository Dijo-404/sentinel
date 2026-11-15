"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useShell } from "@/adapters/shell-context";
import { createAssistantClientForMode } from "@/adapters/composition-peers";
import type {
  AssistantClient,
  AssistantMessage,
  AssistantRole,
  AssistantThread,
} from "@/application/ports";
import { PeerError } from "@/domain/types";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";

type Props = {
  role: AssistantRole;
  /** Root data-testid: operator-assistant | customer-assistant */
  testId: "operator-assistant" | "customer-assistant";
  /** Test override; defaults to mode-wired BFF / fixture client. */
  assistantClient?: AssistantClient | null;
};

type ThreadLoad =
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty"; source: string }
  | {
      status: "ready";
      threads: AssistantThread[];
      source: string;
      label: "live" | "fixture";
    };

type MessageLoad =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; detail: string }
  | { status: "empty"; source: string }
  | {
      status: "ready";
      messages: AssistantMessage[];
      source: string;
    };

/**
 * Assistant threads/messages via same-origin BFF `/api/bff/assistant`.
 * Persists sandbox-labeled text only — never ledger decide / refund mint.
 * Real-peer failure stays visible — never “Not available yet”.
 */
export function AssistantPanel({ role, testId, assistantClient }: Props) {
  const { config } = useShell();
  const client = useMemo(() => {
    if (assistantClient === null) return null;
    if (assistantClient) return assistantClient;
    return createAssistantClientForMode(config.mode);
  }, [assistantClient, config.mode]);

  const threadsTestId = `${testId}-threads`;
  const messagesTestId = `${testId}-messages`;

  const [threadLoad, setThreadLoad] = useState<ThreadLoad>({
    status: "loading",
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messageLoad, setMessageLoad] = useState<MessageLoad>({
    status: "idle",
  });
  const [draft, setDraft] = useState("");
  const [postError, setPostError] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!client) {
        if (!cancelled) {
          setThreadLoad({
            status: "error",
            detail: "Assistant client not configured",
          });
        }
        return;
      }
      try {
        const { threads, source } = await client.listThreads(role);
        if (cancelled) return;
        if (threads.length === 0) {
          setThreadLoad({ status: "empty", source });
          return;
        }
        setThreadLoad({
          status: "ready",
          threads,
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
        setThreadLoad({ status: "error", detail });
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [client, config.mode, role]);

  useEffect(() => {
    if (!selectedId || !client) {
      setMessageLoad({ status: "idle" });
      return;
    }
    let cancelled = false;
    async function run() {
      setMessageLoad({ status: "loading" });
      setPostError(null);
      try {
        const { messages, source } = await client!.listMessages(selectedId!);
        if (cancelled) return;
        if (messages.length === 0) {
          setMessageLoad({ status: "empty", source });
          return;
        }
        setMessageLoad({ status: "ready", messages, source });
      } catch (err) {
        if (cancelled) return;
        const detail =
          err instanceof PeerError
            ? `${err.code}: ${err.message}`
            : err instanceof Error
              ? err.message
              : "Load failed";
        setMessageLoad({ status: "error", detail });
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [client, selectedId]);

  async function onPost(event: FormEvent) {
    event.preventDefault();
    if (!client || !selectedId) return;
    const text = draft.trim();
    if (!text) return;
    setPosting(true);
    setPostError(null);
    try {
      await client.postMessage(selectedId, text);
      setDraft("");
      const { messages, source } = await client.listMessages(selectedId);
      if (messages.length === 0) {
        setMessageLoad({ status: "empty", source });
      } else {
        setMessageLoad({ status: "ready", messages, source });
      }
    } catch (err) {
      const detail =
        err instanceof PeerError
          ? `${err.code}: ${err.message}`
          : err instanceof Error
            ? err.message
            : "Post failed";
      setPostError(detail);
    } finally {
      setPosting(false);
    }
  }

  return (
    <div className="panel stack" data-testid={testId}>
      <h1>Assistant</h1>
      <p className="muted">
        Threads from assistant <code>GET /v1/threads?role={role}</code>. Messages are{" "}
        <code>evidence_mode=sandbox</code> text only — no payment authority.
      </p>
      {config.mode === "fixture" ||
      (threadLoad.status === "ready" && threadLoad.label === "fixture") ? (
        <FixtureBanner />
      ) : null}

      {threadLoad.status === "loading" ? <UiState tone="loading" title="Loading threads…" /> : null}
      {threadLoad.status === "error" ? (
        <div data-testid="peer-error">
          <UiState tone="error" title="Assistant unavailable" detail={threadLoad.detail} />
        </div>
      ) : null}
      {threadLoad.status === "empty" ? (
        <UiState tone="empty" title="No threads" detail="No assistant threads for this role." />
      ) : null}
      {threadLoad.status === "ready" ? (
        <ul className="stack" aria-label="Assistant threads" data-testid={threadsTestId}>
          {threadLoad.threads.map((row) => (
            <li key={row.thread_id}>
              <button
                type="button"
                data-testid={`assistant-thread-${row.thread_id}`}
                aria-pressed={selectedId === row.thread_id}
                onClick={() => setSelectedId(row.thread_id)}
              >
                <strong>{row.title}</strong>
                <span className="mono muted"> {row.thread_id}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {selectedId ? (
        <div className="stack">
          <h2>Messages</h2>
          {messageLoad.status === "loading" ? (
            <UiState tone="loading" title="Loading messages…" />
          ) : null}
          {messageLoad.status === "error" ? (
            <div data-testid="peer-error">
              <UiState tone="error" title="Messages unavailable" detail={messageLoad.detail} />
            </div>
          ) : null}
          {messageLoad.status === "empty" ? (
            <UiState tone="empty" title="No messages" detail="Thread is empty — honest []." />
          ) : null}
          {messageLoad.status === "ready" ? (
            <ul className="stack" aria-label="Assistant messages" data-testid={messagesTestId}>
              {messageLoad.messages.map((m) => (
                <li key={m.message_id} className="stack">
                  <strong>
                    {m.role} <span className="muted">({m.evidence_mode})</span>
                  </strong>
                  <p style={{ margin: 0 }}>{m.text}</p>
                  <p className="muted mono" style={{ margin: 0 }}>
                    {m.created_at}
                  </p>
                </li>
              ))}
            </ul>
          ) : null}

          {postError ? (
            <div data-testid="peer-error">
              <UiState tone="error" title="Message not posted" detail={postError} />
            </div>
          ) : null}

          <form className="stack" onSubmit={onPost}>
            <label>
              Message
              <textarea
                name="text"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={3}
                data-testid="assistant-message-input"
              />
            </label>
            <button
              type="submit"
              disabled={posting || !draft.trim()}
              data-testid="assistant-message-send"
            >
              {posting ? "Sending…" : "Send"}
            </button>
          </form>
        </div>
      ) : null}
    </div>
  );
}
