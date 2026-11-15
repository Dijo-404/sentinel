"use client";

import { motion } from "framer-motion";
import type { CustomerCaseSummary } from "@/application/ports";
import type { CaseState } from "@/domain/types";
import { labelCaseStatus } from "@/domain/status-labels";
import { phaseFor } from "@/components/ledger/case-replay";

const STEPS = ["Received", "Checking", "Approved", "Sent to bank", "Money back"] as const;

/**
 * Customer-language progress. "Money back" only when the provider credit is verified;
 * a refund sent to the bank is still "on its way".
 */
export function customerCopy(status: CaseState): { step: number; headline: string; tone: "pending" | "verified" | "risk" | "neutral" } {
  switch (phaseFor(status).phase) {
    case "Intake":
      return status === "NEEDS_INPUT"
        ? { step: 0, headline: "We need a little more information from you.", tone: "risk" }
        : { step: 0, headline: "We have your report and are looking into it.", tone: "neutral" };
    case "Investigate":
      return { step: 1, headline: "We're checking your order and payment.", tone: "neutral" };
    case "Approve":
      return { step: 1, headline: "Everything checks out. Waiting for final approval.", tone: "pending" };
    case "Dispatch":
      return { step: 3, headline: "On its way. Your bank is processing the refund.", tone: "pending" };
    case "Verify":
      return { step: 3, headline: "Your bank is confirming the refund.", tone: "pending" };
    case "Verified":
      return { step: 4, headline: "Done. The money is back in your account.", tone: "verified" };
    case "Escalated":
      return { step: 1, headline: "A specialist is reviewing your case.", tone: "risk" };
    default:
      return { step: 1, headline: "This case was closed without a refund.", tone: "neutral" };
  }
}

const RING = { pending: "var(--signal)", verified: "var(--ok)", risk: "var(--escalation)", neutral: "var(--signal)" } as const;

export function RefundTracker({ row }: { row: CustomerCaseSummary }) {
  const c = customerCopy(row.status);
  const label = labelCaseStatus(row.status);
  const pct = c.tone === "verified" ? 1 : (c.step + 0.5) / STEPS.length;
  const circ = 2 * Math.PI * 52;
  return (
    <article className="pnl tracker" data-tone={c.tone} aria-label={`Case ${row.case_id}: ${label.text}`}>
      <div className="tracker__ring">
        <svg viewBox="0 0 120 120" aria-hidden="true">
          <circle cx="60" cy="60" r="52" fill="none" stroke="var(--line)" strokeWidth="8" />
          <motion.circle
            cx="60"
            cy="60"
            r="52"
            fill="none"
            stroke={RING[c.tone]}
            strokeWidth="8"
            strokeLinecap="round"
            initial={{ strokeDasharray: `0 ${circ}` }}
            animate={{ strokeDasharray: `${pct * circ} ${circ}` }}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
          />
        </svg>
        <div>
          <strong className="display tnum">{Math.round(pct * 100)}%</strong>
          <small>{label.text}</small>
        </div>
      </div>
      <div className="tracker__body">
        <code className="muted">{row.case_id}</code>
        <p className="tracker__headline">{c.headline}</p>
        <ol className="tracker__steps">
          {STEPS.map((s, i) => {
            const state = i < c.step || (c.tone === "verified" && i === c.step) ? "done" : i === c.step ? "now" : "todo";
            return (
              <li key={s} data-state={state} aria-current={state === "now" ? "step" : undefined}>
                <i aria-hidden="true" />
                <span>{s}</span>
              </li>
            );
          })}
        </ol>
        <p className="muted tracker__meta">
          Update {row.revision} · {row.language}
        </p>
      </div>
    </article>
  );
}
