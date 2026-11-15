import type { Evidence } from "@/domain/types";

export type Freshness = { used: number; state: "fresh" | "expiring" | "expired"; left: string };

/** Share of the evidence validity window already used, from observed_at → expires_at. Pure. */
export function freshness(e: Pick<Evidence, "observed_at" | "expires_at">, now: Date): Freshness {
  const start = Date.parse(e.observed_at);
  const end = Date.parse(e.expires_at);
  const span = Math.max(1, end - start);
  const used = Math.min(1, Math.max(0, (now.getTime() - start) / span));
  const ms = end - now.getTime();
  const state = ms <= 0 ? "expired" : used >= 0.75 ? "expiring" : "fresh";
  const h = Math.floor(Math.abs(ms) / 3_600_000);
  const m = Math.floor((Math.abs(ms) % 3_600_000) / 60_000);
  const left =
    ms <= 0 ? "expired" : h >= 24 ? `${Math.floor(h / 24)}d ${h % 24}h left` : `${h}h ${m}m left`;
  return { used, state, left };
}

const TONE = { fresh: "var(--ok)", expiring: "var(--warn)", expired: "var(--escalation)" } as const;

/** Evidence validity bars. A decision can only rely on evidence that has not expired. */
export function EvidenceFreshness({
  evidence,
  now = new Date(),
}: {
  evidence: Evidence[];
  now?: Date;
}) {
  if (evidence.length === 0) return null;
  return (
    <section className="pnl freshness" aria-label="Evidence freshness">
      <h2>Evidence freshness</h2>
      <ul>
        {evidence.map((e) => {
          const f = freshness(e, now);
          return (
            <li key={e.evidence_id} data-state={f.state}>
              <div className="freshness__row">
                <span className="eyebrow eyebrow--signal">{e.facts.kind}</span>
                <span
                  className="status"
                  data-tone={e.verification_status === "VERIFIED" ? "verified" : "risk"}
                >
                  {e.verification_status.toLowerCase()}
                </span>
                <span className="freshness__left tnum" style={{ color: TONE[f.state] }}>
                  {f.left}
                </span>
              </div>
              <div
                className="freshness__bar"
                role="meter"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(f.used * 100)}
                aria-label={`${e.facts.kind} validity used`}
              >
                <i style={{ width: `${Math.round(f.used * 100)}%`, background: TONE[f.state] }} />
              </div>
              <small className="muted">source {e.source}</small>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
