"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import type { CaseClient } from "@/application/ports";
import type { Case, CaseEvent } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { labelCaseStatus } from "@/domain/status-labels";
import { StatusChip } from "./status-chip";
import { UiState } from "./ui-states";
import { MaskedRef } from "./masked-ref";
import { maskReference } from "@/domain/mask";

const POLL_MS = 5_000;

type Props = {
  caseId: string;
  caseClient: CaseClient;
  /** Show message + escalate controls (operator / supervisor). */
  enableInteractions?: boolean;
};

export function CaseTimeline({
  caseId,
  caseClient,
  enableInteractions = true,
}: Props) {
  const [loading, setLoading] = useState(true);
  const [caseRecord, setCaseRecord] = useState<Case | null>(null);
  const [events, setEvents] = useState<CaseEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [permission, setPermission] = useState<string | null>(null);
  const [messageText, setMessageText] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionOk, setActionOk] = useState<string | null>(null);
  const lastSeq = useRef(0);

  const applyError = useCallback((err: unknown) => {
    if (
      err instanceof PeerError &&
      (err.httpStatus === 403 || err.code === "FORBIDDEN")
    ) {
      setPermission(`${err.code}: ${err.message}`);
    } else if (err instanceof PeerError) {
      setError(`${err.code}: ${err.message}`);
    } else {
      setError(err instanceof Error ? err.message : "Load failed");
    }
  }, []);

  const refresh = useCallback(
    async (opts?: { initial?: boolean }) => {
      if (opts?.initial) {
        setLoading(true);
        setError(null);
        setPermission(null);
      }
      try {
        const [c, ev] = await Promise.all([
          caseClient.getCase(caseId),
          caseClient.listEvents(
            caseId,
            opts?.initial ? undefined : lastSeq.current,
          ),
        ]);
        setCaseRecord(c);
        if (opts?.initial) {
          setEvents(ev.events);
        } else if (ev.events.length > 0) {
          setEvents((prev) => {
            const seen = new Set(prev.map((e) => e.event_id));
            const merged = [...prev];
            for (const e of ev.events) {
              if (!seen.has(e.event_id)) merged.push(e);
            }
            return merged;
          });
        }
        const maxSeq = ev.events.reduce(
          (m, e) => Math.max(m, e.sequence),
          lastSeq.current,
        );
        lastSeq.current = maxSeq;
        setError(null);
        setPermission(null);
      } catch (err) {
        if (opts?.initial) applyError(err);
        // Poll errors stay quiet unless initial load failed.
      } finally {
        if (opts?.initial) setLoading(false);
      }
    },
    [applyError, caseClient, caseId],
  );

  useEffect(() => {
    lastSeq.current = 0;
    void refresh({ initial: true });
    const id = window.setInterval(() => {
      void refresh();
    }, POLL_MS);
    return () => {
      window.clearInterval(id);
    };
  }, [refresh]);

  async function onMessage(e: FormEvent) {
    e.preventDefault();
    if (!caseRecord || !messageText.trim()) return;
    setBusy(true);
    setActionError(null);
    setActionOk(null);
    try {
      const updated = await caseClient.postMessage(caseId, {
        message: messageText.trim(),
        language: caseRecord.language || "en-IN",
        expected_revision: caseRecord.revision,
      });
      setCaseRecord(updated);
      setMessageText("");
      setActionOk("Message sent");
      await refresh({ initial: true });
    } catch (err) {
      setActionError(
        err instanceof PeerError
          ? `${err.code}: ${err.message}`
          : err instanceof Error
            ? err.message
            : "Message failed",
      );
    } finally {
      setBusy(false);
    }
  }

  async function onEscalate() {
    if (!caseRecord) return;
    setBusy(true);
    setActionError(null);
    setActionOk(null);
    try {
      const updated = await caseClient.escalate(caseId, {
        expected_revision: caseRecord.revision,
        reason_code: "OPERATOR_ESCALATION",
        owner_queue: "supervisor",
      });
      setCaseRecord(updated);
      setActionOk("Escalated — handoff, not resolution");
      await refresh({ initial: true });
    } catch (err) {
      setActionError(
        err instanceof PeerError
          ? `${err.code}: ${err.message}`
          : err instanceof Error
            ? err.message
            : "Escalate failed",
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <UiState tone="loading" title="Loading case timeline…" />;
  if (permission) {
    return (
      <UiState
        tone="permission"
        title="Permission denied"
        detail={permission}
      />
    );
  }
  if (error)
    return <UiState tone="error" title="Timeline unavailable" detail={error} />;
  if (!caseRecord)
    return <UiState tone="empty" title="No case" detail="Case not found." />;

  return (
    <div className="stack" data-testid="case-timeline">
      <div className="row">
        <h1>Case timeline</h1>
        <StatusChip label={labelCaseStatus(caseRecord.status)} />
      </div>
      <p className="muted">
        Case{" "}
        <MaskedRef
          label="case_id"
          masked={maskReference(caseRecord.case_id, "case-…")}
        />{" "}
        · revision {caseRecord.revision} · intent {caseRecord.intent}
      </p>
      <p className="muted" data-testid="timeline-poll-hint">
        Live updates every {POLL_MS / 1000}s via listEvents.
      </p>
      {events.length === 0 ? (
        <UiState
          tone="empty"
          title="No events yet"
          detail="Timeline is empty."
        />
      ) : (
        <ol className="timeline panel" aria-label="Case events">
          {events.map((event) => (
            <li key={event.event_id}>
              <div className="row">
                <strong>{event.type}</strong>
                <StatusChip label={labelCaseStatus(event.payload.status)} />
                <span className="muted mono">{event.occurred_at}</span>
              </div>
              <p className="muted" style={{ margin: "0.25rem 0 0" }}>
                reason={event.payload.reason_code}
                {event.payload.action_id
                  ? ` · action=${maskReference(event.payload.action_id, "act-…")}`
                  : ""}
              </p>
            </li>
          ))}
        </ol>
      )}

      {enableInteractions ? (
        <div className="panel stack" data-testid="case-interactions">
          <h2>Case actions</h2>
          <p className="muted">
            Message updates the case; escalate is a handoff, not resolution.
          </p>
          <form className="stack" onSubmit={(e) => void onMessage(e)}>
            <label>
              Message
              <textarea
                data-testid="case-message-input"
                value={messageText}
                onChange={(ev) => setMessageText(ev.target.value)}
                rows={3}
                disabled={busy}
              />
            </label>
            <div className="row">
              <button
                type="submit"
                data-testid="case-message-submit"
                disabled={busy || !messageText.trim()}
              >
                Send message
              </button>
              <button
                type="button"
                data-testid="case-escalate"
                disabled={busy || caseRecord.status === "ESCALATED"}
                onClick={() => void onEscalate()}
              >
                Escalate
              </button>
            </div>
          </form>
          {actionError ? (
            <p role="alert" data-testid="case-action-error">
              {actionError}
            </p>
          ) : null}
          {actionOk ? (
            <p role="status" data-testid="case-action-ok">
              {actionOk}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
