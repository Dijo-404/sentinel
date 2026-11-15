"use client";

import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import type { CaseEvent, CaseState } from "@/domain/types";
import { labelCaseStatus } from "@/domain/status-labels";

export type MoneyAt = "merchant" | "in-flight" | "customer" | "none";
export type Phase = { phase: string; money: MoneyAt; tone: "neutral" | "pending" | "verified" | "risk"; caption: string };

/**
 * Where the money is for a case status. Only VERIFIED_RESOLVED reaches the customer;
 * dispatch and verifying stay "in flight" because pending is not proof.
 */
export function phaseFor(status: CaseState): Phase {
  switch (status) {
    case "RECEIVED":
    case "NEEDS_INPUT":
      return { phase: "Intake", money: "merchant", tone: "neutral", caption: "Money with merchant" };
    case "INVESTIGATING":
    case "RECONCILING":
      return { phase: "Investigate", money: "merchant", tone: "neutral", caption: "Money with merchant" };
    case "PLANNING":
    case "POLICY_CHECK":
    case "WAITING_APPROVAL":
      return { phase: "Approve", money: "merchant", tone: "pending", caption: "Awaiting exact approval · nothing moved" };
    case "EXECUTING":
    case "WAITING_EXTERNAL":
      return { phase: "Dispatch", money: "in-flight", tone: "pending", caption: "In flight · pending is not proof" };
    case "VERIFYING":
      return { phase: "Verify", money: "in-flight", tone: "pending", caption: "Checking provider postconditions" };
    case "VERIFIED_RESOLVED":
      return { phase: "Verified", money: "customer", tone: "verified", caption: "Credit verified" };
    case "ESCALATED":
      return { phase: "Escalated", money: "merchant", tone: "risk", caption: "Handed off · not resolved" };
    case "CLOSED_NO_ACTION":
      return { phase: "Closed", money: "none", tone: "neutral", caption: "Closed with no money movement" };
  }
}

const X: Record<MoneyAt, number> = { merchant: 0, "in-flight": 235, customer: 470, none: 0 };
const TOKEN: Record<Phase["tone"], string> = {
  neutral: "var(--fog)",
  pending: "var(--signal)",
  verified: "var(--verified)",
  risk: "var(--ember)",
};

/** Scrub or play a case's real event history and watch where the money is at each step. */
export function CaseReplay({ events }: { events: CaseEvent[] }) {
  const sorted = [...events].sort((a, b) => a.sequence - b.sequence);
  const last = sorted.length - 1;
  const [i, setI] = useState(last);
  const [playing, setPlaying] = useState(false);
  const timer = useRef<number | null>(null);
  const following = useRef(true);

  // Stay on the newest event as live polling appends, unless the user scrubbed back.
  useEffect(() => {
    if (following.current) setI(last);
  }, [last]);

  useEffect(() => () => {
    if (timer.current) window.clearInterval(timer.current);
  }, []);

  if (sorted.length === 0) return null;
  const at = Math.min(i, last);
  const ev = sorted[at];
  const p = phaseFor(ev.payload.status);

  function seek(n: number) {
    following.current = n >= last;
    setI(n);
  }

  function play() {
    if (playing) {
      if (timer.current) window.clearInterval(timer.current);
      setPlaying(false);
      return;
    }
    setPlaying(true);
    let n = at >= last ? 0 : at;
    seek(n);
    timer.current = window.setInterval(() => {
      n += 1;
      if (n > last) {
        if (timer.current) window.clearInterval(timer.current);
        setPlaying(false);
        return;
      }
      seek(n);
    }, 1100);
  }

  return (
    <section className="pnl replay" aria-label="Case replay">
      <div className="replay__head">
        <h2>Case replay</h2>
        <span className="tnum replay__pos">
          step {at + 1} / {sorted.length}
        </span>
        <div className="replay__controls">
          <button type="button" className="topbar__icon" aria-label="Previous event" onClick={() => seek(Math.max(0, at - 1))} disabled={at === 0}>
            ‹
          </button>
          <button type="button" className="btn btn-primary" onClick={play}>
            {playing ? "Pause" : "Replay"}
          </button>
          <button type="button" className="topbar__icon" aria-label="Next event" onClick={() => seek(Math.min(last, at + 1))} disabled={at === last}>
            ›
          </button>
        </div>
      </div>
      <input
        className="replay__scrub"
        type="range"
        min={0}
        max={last}
        value={at}
        onChange={(e) => seek(Number(e.target.value))}
        aria-label="Replay position"
        aria-valuetext={`${labelCaseStatus(ev.payload.status).text}, event ${at + 1} of ${sorted.length}`}
      />
      <div className="replay__body">
        <svg viewBox="0 0 620 170" width="100%" role="img" aria-label={`Money position: ${p.caption}`} className="replay__map">
          {(["Merchant", "Provider", "Customer"] as const).map((name, k) => (
            <g key={name}>
              <rect x={10 + k * 235} y={60} width={130} height={64} rx={14} fill="var(--surface)" stroke={k === 2 && p.money === "customer" ? "var(--verified)" : k === 1 && p.money === "in-flight" ? "var(--signal)" : "var(--line-strong)"} />
              <text x={75 + k * 235} y={97} textAnchor="middle" fontSize={13} fontWeight={600} fill="var(--ink)">
                {name}
              </text>
            </g>
          ))}
          <path d="M140 92 H245 M375 92 H480" stroke="var(--line-strong)" strokeWidth={2} />
          {p.money !== "merchant" && p.money !== "none" && <path d="M140 92 H245" stroke="var(--signal)" strokeWidth={2} className="flow-dash" />}
          {p.money === "customer" && <path d="M375 92 H480" stroke="var(--verified)" strokeWidth={2} className="flow-dash" />}
          {p.money !== "none" && (
            <motion.circle cy={38} r={14} fill={TOKEN[p.tone]} initial={false} animate={{ cx: 75 + X[p.money] }} transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }} />
          )}
          <text x={310} y={160} textAnchor="middle" fontFamily="var(--mono)" fontSize={11} fill={TOKEN[p.tone]}>
            {p.caption}
          </text>
        </svg>
        <div className="replay__event" key={ev.event_id}>
          <span className="eyebrow eyebrow--signal">{p.phase}</span>
          <strong>{ev.type}</strong>
          <span className="status" data-tone={p.tone === "neutral" ? undefined : p.tone}>
            {labelCaseStatus(ev.payload.status).text}
          </span>
          <time className="muted" dateTime={ev.occurred_at}>
            {new Date(ev.occurred_at).toLocaleString()}
          </time>
          <code className="muted">reason={ev.payload.reason_code}</code>
        </div>
      </div>
    </section>
  );
}
