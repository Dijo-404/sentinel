"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CaseClient } from "@/application/ports";
import type { Case, CaseEvent } from "@/domain/types";
import { PeerError } from "@/domain/types";
import { labelCaseStatus } from "@/domain/status-labels";
import { StatusChip } from "./status-chip";
import { UiState } from "./ui-states";
import { MaskedRef } from "./masked-ref";
import { maskReference } from "@/domain/mask";
import { CaseReplay, phaseFor } from "./ledger/case-replay";

type Props = {
  caseClient: CaseClient;
};

const TRACK = ["Intake", "Investigate", "Approve", "Dispatch", "Verify"] as const;

export type QueueFilter = "all" | "work" | "waiting" | "escalated";

/** Which filter tab a case belongs to. Pure. */
export function filterOf(c: Case): Exclude<QueueFilter, "all"> | "done" {
  const p = phaseFor(c.status).phase;
  if (p === "Escalated") return "escalated";
  if (p === "Intake" || p === "Investigate") return "work";
  if (p === "Verified" || p === "Closed") return "done";
  return "waiting";
}

function isTyping(el: EventTarget | null) {
  const t = el as HTMLElement | null;
  return (
    !!t &&
    (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)
  );
}

/** Operator workbench: filterable queue, J/K selection, and a live replay preview of the selected case. */
export function OperatorQueue({ caseClient }: Props) {
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState<Case[]>([]);
  const [nextCursor, setNextCursor] = useState<string | undefined>();
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [permission, setPermission] = useState<string | null>(null);
  const [filter, setFilter] = useState<QueueFilter>("all");
  const [selected, setSelected] = useState(0);
  const [preview, setPreview] = useState<{
    id: string;
    events: CaseEvent[] | null;
    error?: string;
  } | null>(null);
  const tableRef = useRef<HTMLTableElement>(null);

  const loadPage = useCallback(
    async (after?: string, append = false) => {
      if (append) setLoadingMore(true);
      else {
        setLoading(true);
        setError(null);
        setPermission(null);
      }
      try {
        const result = await caseClient.listOpsCases(after ? { after } : undefined);
        setCases((prev) => (append ? [...prev, ...result.cases] : result.cases));
        setNextCursor(result.next_cursor);
      } catch (err) {
        if (err instanceof PeerError && (err.httpStatus === 403 || err.code === "FORBIDDEN")) {
          setPermission(`${err.code}: ${err.message}`);
        } else if (err instanceof PeerError) {
          setError(`${err.code}: ${err.message}`);
        } else {
          setError(err instanceof Error ? err.message : "Load failed");
        }
        if (!append) setCases([]);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [caseClient],
  );

  useEffect(() => {
    void loadPage();
  }, [loadPage]);

  const counts = useMemo(() => {
    const out = { all: cases.length, work: 0, waiting: 0, escalated: 0 };
    for (const c of cases) {
      const f = filterOf(c);
      if (f !== "done") out[f]++;
    }
    return out;
  }, [cases]);
  const visible = useMemo(
    () => (filter === "all" ? cases : cases.filter((c) => filterOf(c) === filter)),
    [cases, filter],
  );
  const sel = visible[Math.min(selected, Math.max(0, visible.length - 1))];
  const selId = sel?.case_id;

  // Load the selected case's real events for the preview pane.
  useEffect(() => {
    if (!selId) return;
    let cancelled = false;
    setPreview({ id: selId, events: null });
    caseClient
      .listEvents(selId)
      .then((r) => {
        if (!cancelled) setPreview({ id: selId, events: r.events });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setPreview({
            id: selId,
            events: [],
            error: err instanceof PeerError ? `${err.code}: ${err.message}` : "Events unavailable",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [caseClient, selId]);

  // Latest list/selection for the key handler, so it never acts on a stale snapshot.
  const live = useRef({ visible, selected });
  live.current = { visible, selected };

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const { visible: rows, selected: at } = live.current;
      if (isTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey || rows.length === 0) return;
      const k = e.key.toLowerCase();
      if (k === "j" || k === "arrowdown") setSelected(Math.min(rows.length - 1, at + 1));
      else if (k === "k" || k === "arrowup") setSelected(Math.max(0, at - 1));
      else if (k === "enter" || k === "e") {
        const id = rows[Math.min(at, rows.length - 1)]?.case_id;
        if (!id) return;
        const testId = k === "e" ? `evidence-link-${id}` : `timeline-link-${id}`;
        // Click the real Link so navigation stays client-side and no router is required.
        tableRef.current
          ?.querySelector<HTMLAnchorElement>(`[data-testid="${CSS.escape(testId)}"]`)
          ?.click();
      } else return;
      e.preventDefault();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (loading) {
    return (
      <div className="wb" aria-busy="true">
        <UiState tone="loading" title="Loading operator queue…" />
        <div className="wb__skeleton" aria-hidden="true">
          {[0, 1, 2, 3, 4].map((i) => (
            <span key={i} className="skeleton" style={{ height: 52 }} />
          ))}
        </div>
      </div>
    );
  }
  if (permission) {
    return <UiState tone="permission" title="Permission denied" detail={permission} />;
  }
  if (error) return <UiState tone="error" title="Queue unavailable" detail={error} />;
  if (cases.length === 0) {
    return <UiState tone="empty" title="Queue empty" detail="No cases in scope." />;
  }

  const tabs: { key: QueueFilter; label: string }[] = [
    { key: "all", label: "All" },
    { key: "work", label: "To work" },
    { key: "waiting", label: "Waiting" },
    { key: "escalated", label: "Escalated" },
  ];
  const selPhase = sel ? phaseFor(sel.status) : null;
  const done = counts.all - counts.work - counts.waiting - counts.escalated;

  return (
    <div className="stack wb" data-testid="operator-queue-list">
      <div className="wb__head">
        <div>
          <p className="eyebrow">Queue · tenant scoped</p>
          <h1>Operator queue</h1>
          <p className="muted">Tenant-scoped cases. Escalation is a handoff, not resolution.</p>
        </div>
        <div className="pill-tabs" role="tablist" aria-label="Filter cases">
          {tabs.map((t) => (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={filter === t.key}
              onClick={() => {
                setFilter(t.key);
                setSelected(0);
              }}
            >
              {t.label}{" "}
              <span className="tnum" style={{ opacity: 0.6 }}>
                {counts[t.key]}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div
        className="wb__dist"
        role="img"
        aria-label={`To work ${counts.work}, waiting ${counts.waiting}, escalated ${counts.escalated}, done ${done}`}
      >
        <i style={{ flexGrow: counts.work, background: "var(--signal)" }} />
        <i style={{ flexGrow: counts.waiting, background: "var(--tide)" }} />
        <i style={{ flexGrow: counts.escalated, background: "var(--ember)" }} />
        <i style={{ flexGrow: done, background: "var(--verified)" }} />
      </div>

      <div className="wb__split">
        <div className="pnl wb__list">
          <div className="table-scroll">
            <table className="table" aria-label="Operator cases" ref={tableRef}>
              <thead>
                <tr>
                  <th scope="col">Case</th>
                  <th scope="col">Status</th>
                  <th scope="col">Progress</th>
                  <th scope="col">Intent</th>
                  <th scope="col">Revision</th>
                  <th scope="col">Evidence</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((c, i) => {
                  const p = phaseFor(c.status);
                  const step = TRACK.indexOf(p.phase as (typeof TRACK)[number]);
                  const verified = p.phase === "Verified";
                  const href = `/operator/cases/${encodeURIComponent(c.case_id)}`;
                  return (
                    <tr
                      key={c.case_id}
                      aria-selected={c === sel}
                      onClick={() => setSelected(i)}
                      className="wb__row"
                    >
                      <td>
                        <Link href={href}>
                          <MaskedRef label="case_id" masked={maskReference(c.case_id, "case-…")} />
                        </Link>
                      </td>
                      <td>
                        <StatusChip label={labelCaseStatus(c.status)} />
                      </td>
                      <td>
                        <span className="wb__track" title={p.phase} data-tone={p.tone}>
                          {TRACK.map((t, k) => (
                            <i key={t} data-on={verified || (step >= 0 && k <= step) || undefined} />
                          ))}
                          <span className="sr-only">{p.phase}</span>
                        </span>
                      </td>
                      <td>{c.intent}</td>
                      <td className="mono">{c.revision}</td>
                      <td>
                        <Link href={`${href}/evidence`} data-testid={`evidence-link-${c.case_id}`}>
                          Open evidence
                        </Link>
                        {" · "}
                        <Link href={href} data-testid={`timeline-link-${c.case_id}`}>
                          Timeline
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {visible.length === 0 && (
            <UiState tone="empty" title="Nothing in this filter" detail="Try another tab." />
          )}
          <p className="wb__keys">
            <kbd className="kbd">J</kbd>/<kbd className="kbd">K</kbd> move · <kbd className="kbd">↵</kbd>{" "}
            timeline · <kbd className="kbd">E</kbd> evidence
          </p>
        </div>

        {sel && selPhase && (
          <aside className="pnl wb__preview" aria-label="Selected case preview" key={sel.case_id}>
            <span className="eyebrow eyebrow--signal">{selPhase.phase}</span>
            <h2>
              <MaskedRef label="case_id" masked={maskReference(sel.case_id, "case-…")} />
            </h2>
            <dl className="wb__facts">
              <div>
                <dt>Intent</dt>
                <dd>{sel.intent}</dd>
              </div>
              <div>
                <dt>Revision</dt>
                <dd className="tnum">{sel.revision}</dd>
              </div>
              <div>
                <dt>Evidence</dt>
                <dd className="tnum">{sel.evidence_ids.length}</dd>
              </div>
              <div>
                <dt>Money</dt>
                <dd>{selPhase.caption}</dd>
              </div>
            </dl>
            {preview?.id === sel.case_id && preview.events === null && (
              <span className="skeleton" style={{ height: 180 }} aria-hidden="true" />
            )}
            {preview?.id === sel.case_id && preview.error && (
              <UiState tone="error" title="Events unavailable" detail={preview.error} />
            )}
            {preview?.id === sel.case_id && preview.events && preview.events.length > 0 && (
              <CaseReplay events={preview.events} />
            )}
            <div className="row">
              <Link className="btn btn-primary" href={`/operator/cases/${encodeURIComponent(sel.case_id)}`}>
                Open case
              </Link>
              <Link
                className="btn btn-glass"
                href={`/operator/cases/${encodeURIComponent(sel.case_id)}/evidence`}
              >
                Evidence
              </Link>
            </div>
          </aside>
        )}
      </div>

      {nextCursor ? (
        <button
          type="button"
          data-testid="queue-load-more"
          disabled={loadingMore}
          onClick={() => void loadPage(nextCursor, true)}
        >
          {loadingMore ? "Loading…" : "Load more"}
        </button>
      ) : null}
    </div>
  );
}
