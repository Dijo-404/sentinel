"use client";

import { motion } from "framer-motion";
import type { MerchantMetrics } from "@/application/ports";
import { formatMoney } from "@/components/ledger/money";

/** "0.4000" or "4.2%" → fraction 0..1, or null if unparseable. Pure. */
export function parseRate(raw: string): number | null {
  const s = raw.trim();
  const n = Number.parseFloat(s.replace("%", ""));
  if (!Number.isFinite(n)) return null;
  const f = s.endsWith("%") ? n / 100 : n;
  return f >= 0 && f <= 1 ? f : null;
}

/** 2700 → "45m"; 112320 → "1d 7h". Pure. */
export function humanDuration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  const d = Math.floor(s / 86_400);
  const h = Math.floor((s % 86_400) / 3_600);
  const m = Math.floor((s % 3_600) / 60);
  if (d) return `${d}d ${h}h`;
  if (h) return `${h}h ${m}m`;
  return m ? `${m}m` : `${s}s`;
}

const day = (iso: string) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toISOString().slice(0, 10);
};

/** Visual layer over the real MerchantMetrics projection. Draws only what the wire provides. */
export function MerchantMetricsViz({ m }: { m: MerchantMetrics }) {
  const rate = parseRate(m.exception_rate);
  const buckets = Object.entries(m.refund_aging_buckets);
  const maxBucket = Math.max(1, ...buckets.map(([, v]) => v));
  const totalAging = buckets.reduce((a, [, v]) => a + v, 0);
  const circ = 2 * Math.PI * 50;

  return (
    <div className="mviz" data-testid="merchant-metrics-viz">
      <p className="lk-chart__meta">
        Window {day(m.window_start)} → {day(m.window_end)} · {m.merchant_ref}
      </p>
      <div className="mviz__grid">
        <section className="pnl pnl--pad mviz__hero" aria-label="Unresolved value">
          <span className="lk-chart__meta">Unresolved value</span>
          <strong className="display mviz__big tnum">
            {formatMoney(m.unresolved_minor, m.currency)}
          </strong>
          <span className="lk-chart__meta">
            Median handling {humanDuration(m.median_handling_seconds)}
          </span>
        </section>

        <section className="pnl pnl--pad mviz__gauge" aria-label="Exception rate">
          <span className="lk-chart__meta">Exception rate</span>
          {rate === null ? (
            <p className="muted">Unreadable rate “{m.exception_rate}”</p>
          ) : (
            <div className="mviz__ring">
              <svg viewBox="0 0 120 120" aria-hidden="true">
                <circle cx="60" cy="60" r="50" fill="none" stroke="var(--line)" strokeWidth="10" />
                <motion.circle
                  cx="60"
                  cy="60"
                  r="50"
                  fill="none"
                  stroke={
                    rate > 0.25 ? "var(--escalation)" : rate > 0.1 ? "var(--warn)" : "var(--ok)"
                  }
                  strokeWidth="10"
                  strokeLinecap="round"
                  initial={{ strokeDasharray: `0 ${circ}` }}
                  animate={{ strokeDasharray: `${rate * circ} ${circ}` }}
                  transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
                />
              </svg>
              <strong className="display tnum">{(rate * 100).toFixed(1)}%</strong>
            </div>
          )}
        </section>

        <section className="pnl pnl--pad mviz__aging" aria-label="Refund aging">
          <div className="lk-chart__head">
            <span className="lk-chart__meta">Refund aging</span>
            <span className="lk-chart__meta tnum">{totalAging} open</span>
          </div>
          {buckets.length === 0 ? (
            <p className="muted">No aging buckets in this window.</p>
          ) : (
            <ul className="mviz__bars">
              {buckets.map(([k, v], i) => (
                <li key={k}>
                  <span className="mviz__bar-track">
                    <motion.i
                      initial={{ height: 0 }}
                      animate={{ height: `${(v / maxBucket) * 100}%` }}
                      transition={{ duration: 0.7, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] }}
                      style={{
                        background:
                          i >= buckets.length - 1
                            ? "var(--escalation)"
                            : `color-mix(in srgb, var(--signal) ${90 - i * 15}%, var(--ember))`,
                      }}
                    />
                  </span>
                  <strong className="tnum">{v}</strong>
                  <small>{k}</small>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="pnl pnl--pad mviz__causes" aria-label="Top causes">
          <span className="lk-chart__meta">Top causes (ranked)</span>
          <ol>
            {m.top_causes.map((c, i) => (
              <li key={c} style={{ animationDelay: `${i * 60}ms` }}>
                <span className="tnum">{i + 1}</span>
                {c.replace(/_/g, " ").toLowerCase()}
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  );
}
