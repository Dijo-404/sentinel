"use client";

import { useEffect, useState } from "react";
import type { CaseClient } from "@/application/ports";
import type { Case, CaseEvent } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { labelCaseStatus } from "@/domain/status-labels";
import { StatusChip } from "./status-chip";
import { UiState } from "./ui-states";
import { MaskedRef } from "./masked-ref";
import { maskReference } from "@/domain/mask";

type Props = {
  caseId: string;
  caseClient: CaseClient;
};

export function CaseTimeline({ caseId, caseClient }: Props) {
  const [loading, setLoading] = useState(true);
  const [caseRecord, setCaseRecord] = useState<Case | null>(null);
  const [events, setEvents] = useState<CaseEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [permission, setPermission] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      setPermission(null);
      try {
        const [c, ev] = await Promise.all([
          caseClient.getCase(caseId),
          caseClient.listEvents(caseId),
        ]);
        if (cancelled) return;
        setCaseRecord(c);
        setEvents(ev.events);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof PeerError && (err.httpStatus === 403 || err.code === "FORBIDDEN")) {
          setPermission(`${err.code}: ${err.message}`);
        } else if (err instanceof PeerError) {
          setError(`${err.code}: ${err.message}`);
        } else {
          setError(err instanceof Error ? err.message : "Load failed");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [caseId, caseClient]);

  if (loading) return <UiState tone="loading" title="Loading case timeline…" />;
  if (permission) {
    return <UiState tone="permission" title="Permission denied" detail={permission} />;
  }
  if (error) return <UiState tone="error" title="Timeline unavailable" detail={error} />;
  if (!caseRecord) return <UiState tone="empty" title="No case" detail="Case not found." />;

  return (
    <div className="stack">
      <div className="row">
        <h1>Case timeline</h1>
        <StatusChip label={labelCaseStatus(caseRecord.status)} />
      </div>
      <p className="muted">
        Case{" "}
        <MaskedRef label="case_id" masked={maskReference(caseRecord.case_id, "case-…")} />{" "}
        · revision {caseRecord.revision} · intent {caseRecord.intent}
      </p>
      {events.length === 0 ? (
        <UiState tone="empty" title="No events yet" detail="Timeline is empty." />
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
    </div>
  );
}
