"use client";

import Link from "next/link";
import { AnimatePresence, motion, useScroll, useTransform, type MotionValue } from "framer-motion";
import { useRef, useState } from "react";
import { Reveal } from "@/components/motion/reveal";
import { HoverArea, Sparkline } from "@/components/ledger/charts";
import { formatMoney } from "@/components/ledger/money";
import { FooterWordmark } from "../footer-wordmark";
import { DEMO_CURRENCY } from "./hero";
import { ATTACKS, FAULTS, LAYERS, STAGES, advance, checkStates, inject, isResolved, limitCheck, type Fault, type SimState } from "./model";

const EASE = [0.22, 1, 0.36, 1] as const;
const money = (major: number) => formatMoney(Math.round(major * 100), DEMO_CURRENCY).replace(/\.00$/, "");

export function Ticker() {
  const items = [
    ["rfnd_••7Q2K  ₹12,900", ""],
    ["✓ credited", "var(--ok)"],
    ["case_••91A  investigate", ""],
    ["disp_••0F3  approved", "var(--periwinkle)"],
    ["rfnd_••2MX  pending", "var(--provider)"],
    ["case_••7DE  escalated", "var(--escalation)"],
  ];
  return (
    <section className="ticker" aria-label="Recent ledger entries">
      <div className="ticker__track">
        {[...items, ...items].map(([text, color], i) => (
          <span key={i} style={{ color: color || undefined }} aria-hidden={i >= items.length || undefined}>
            {text}
          </span>
        ))}
      </div>
    </section>
  );
}

const PROBLEM = [
  "Refunds fail quietly.",
  "A timeout becomes a double payout.",
  "An approval gets reused for a different amount.",
  "A pending status closes the ticket.",
  "Pending is not proof.",
];

function LitPhrase({ text, i, progress, accent }: { text: string; i: number; progress: MotionValue<number>; accent?: boolean }) {
  const start = i / PROBLEM.length;
  const opacity = useTransform(progress, [start, start + 0.18], [0.14, 1]);
  return (
    <motion.span style={{ opacity, color: accent ? "var(--primary)" : undefined }}>{text} </motion.span>
  );
}

/** Pinned paragraph whose phrases light up with scroll. */
export function Problem() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 0.8", "end 0.6"] });
  return (
    <section ref={ref} className="lp-problem">
      <p>
        {PROBLEM.map((t, i) => (
          <LitPhrase key={t} text={t} i={i} progress={scrollYProgress} accent={i === PROBLEM.length - 1} />
        ))}
      </p>
    </section>
  );
}

export function Simulator() {
  const [s, setS] = useState<SimState>({ step: 0, fault: null });
  const done = isResolved(s);
  const checks = checkStates(s);
  const fault = s.fault ? FAULTS[s.fault] : null;
  const pct = Math.min(100, s.step * 25);
  const cta = s.fault ? "Clear the fault to continue" : s.step === 0 ? "Start case" : s.step >= STAGES.length ? "Run again" : "Next stage";

  return (
    <section id="simulator" className="lp-section">
      <div className="lp-wrap">
        <Reveal className="lp-head">
          <div>
            <p className="eyebrow eyebrow--signal">Case simulator · try it</p>
            <h2>Push a refund through. Then try to break it.</h2>
          </div>
          <div className="lp-head__actions">
            <button type="button" className="btn btn-glass" onClick={() => setS({ step: 0, fault: null })}>Reset</button>
            <button type="button" className="btn btn-lime" onClick={() => setS(advance(s))} disabled={Boolean(s.fault)}>{cta}</button>
          </div>
        </Reveal>

        <div className="pnl lp-sim">
          <ol className="lp-sim__track" aria-label="Case stages">
            <div className="lp-sim__rail" aria-hidden="true">
              <motion.i animate={{ width: `${pct}%` }} transition={{ duration: 0.7, ease: EASE }} data-done={done || undefined} />
            </div>
            {STAGES.map((st, i) => {
              const state = s.fault && i === s.step - 1 ? "blocked" : i < s.step ? (i === STAGES.length - 1 ? "verified" : "past") : i === s.step ? "current" : "todo";
              return (
                <li key={st.title} data-state={state} aria-current={i === s.step ? "step" : undefined}>
                  <span className="lp-sim__node">{i < s.step && state !== "blocked" ? "✓" : `0${i + 1}`}</span>
                  <strong>{st.title}</strong>
                  <small>{st.sub}</small>
                </li>
              );
            })}
          </ol>

          <div className="lp-sim__body">
            <div>
              <h3 className="eyebrow">Server checks</h3>
              <ul className="lp-sim__checks">
                <AnimatePresence initial={false}>
                  {checks.map((c) => (
                    <motion.li key={c.code} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} data-ok={c.ok}>
                      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" strokeWidth="2" aria-hidden="true">
                        <path d={c.ok ? "M3 9.5l4 4 8-9" : "M4 4l10 10M14 4L4 14"} />
                      </svg>
                      {c.text}
                      <code>{c.code}</code>
                    </motion.li>
                  ))}
                </AnimatePresence>
                {checks.length === 0 && <li className="lp-sim__empty">Start the case to watch checks pass.</li>}
              </ul>
            </div>
            <div>
              <h3 className="eyebrow">Inject a failure</h3>
              <div className="lp-sim__faults">
                {(Object.keys(FAULTS) as Fault[]).map((f) => (
                  <button key={f} type="button" aria-pressed={s.fault === f} onClick={() => setS(inject(s, f))}>
                    <strong>{FAULTS[f].title}</strong>
                    <small>{FAULTS[f].detail}</small>
                  </button>
                ))}
              </div>
              <div className={`lp-sim__out ${fault ? "shake" : ""}`} data-tone={fault ? "risk" : done ? "verified" : undefined} aria-live="polite" key={`${s.fault}-${done}`}>
                <span className="eyebrow">{fault ? fault.tag : done ? "RESOLVED" : `STAGE ${Math.min(s.step + 1, 5)} OF 5`}</span>
                <strong>{fault ? fault.outcome : done ? "₹4,250 back on card ••••4417" : STAGES[Math.min(s.step, 4)].title}</strong>
                <p>
                  {fault
                    ? fault.body
                    : done
                      ? "The provider confirmed the credit and every postcondition passed. Financial audit written. Only now does the case close."
                      : "Advance the case, or inject a failure to see how Sentinel reacts."}
                </p>
                {done && <span className="stamp lp-sim__stamp">CREDIT VERIFIED</span>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Guardrails() {
  const [a, setA] = useState(0);
  const hit = ATTACKS[a].blockedBy;
  return (
    <section id="guardrails" className="lp-section lp-paper">
      <div className="lp-wrap">
        <Reveal className="lp-head">
          <h2>
            Models propose. <span className="lp-paper__accent">The server decides.</span>
          </h2>
          <p className="lp-head__lead">Pick a move the model might try. Watch which layer blocks it.</p>
        </Reveal>
        <div className="lp-guard">
          <div className="lp-guard__attacks" role="radiogroup" aria-label="Attempted model action">
            {ATTACKS.map((x, i) => (
              <button key={x.text} type="button" role="radio" aria-checked={i === a} onClick={() => setA(i)}>
                <span className="eyebrow">Model tries</span>
                {x.text}
              </button>
            ))}
          </div>
          <ol className="lp-guard__layers">
            {LAYERS.map((l, i) => (
              <motion.li key={l.title} data-blocked={i === hit || undefined} animate={{ x: i === hit ? -12 : 0 }} transition={{ duration: 0.35, ease: EASE }}>
                <span className="tnum">0{i + 1}</span>
                <div>
                  <strong>{l.title}</strong>
                  <small>{l.sub}</small>
                </div>
                <em>{i === hit ? "BLOCKED" : "pass-through"}</em>
              </motion.li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

const DATASETS = [
  { label: "Refund requests", sla: 0.94, hours: 31, base: 60, amp: 22, ph: 0 },
  { label: "Disputes", sla: 0.88, hours: 44, base: 28, amp: 12, ph: 1.4 },
  { label: "Duplicate charges", sla: 0.97, hours: 19, base: 18, amp: 9, ph: 2.6 },
];

export function Analytics() {
  const [d, setD] = useState(0);
  const [amount, setAmount] = useState(24000);
  const ds = DATASETS[d];
  const vals = Array.from({ length: 30 }, (_, i) => Math.round(ds.base + ds.amp * Math.sin(i / 4 + ds.ph) + i * 0.9 + ((i * 7) % 5)));
  const ver = vals.map((v, i) => Math.round(v * (0.78 + 0.12 * Math.cos(i / 5))));
  const labels = vals.map((_, i) => `Nov ${i + 1}`);
  const lim = limitCheck(amount, 128000, 200000);
  const heat = Array.from({ length: 7 }, (_, di) =>
    Array.from({ length: 24 }, (_, h) => Math.max(0, Math.sin(((h - 7 + ds.ph) / 24) * Math.PI) * (di < 5 ? 1 : 0.5) + ((di * 5 + h * 11 + d * 3) % 9) / 28)),
  );

  return (
    <section id="analytics" className="lp-section">
      <div className="lp-wrap">
        <Reveal className="lp-head">
          <h2>Every number can be interrogated</h2>
          <div className="pill-tabs" role="tablist" aria-label="Exception type">
            {DATASETS.map((x, i) => (
              <button key={x.label} type="button" role="tab" aria-selected={i === d} onClick={() => setD(i)}>
                {x.label}
              </button>
            ))}
          </div>
        </Reveal>
        <div className="lp-bento">
          <Reveal className="pnl pnl--pad pnl--interactive lp-bento__wide">
            <HoverArea
              caption={`${ds.label}, daily, 30 days`}
              primary={vals}
              secondary={ver}
              labels={labels}
              render={(i) => (
                <>
                  <div>
                    <span className="lk-chart__meta">{ds.label} · {labels[i]} · hover the chart</span>
                    <div className="lk-chart__value tnum">{vals[i]} cases</div>
                  </div>
                  <span className="status" data-tone="verified">{ver[i]} verified</span>
                </>
              )}
            />
          </Reveal>
          <Reveal className="pnl pnl--pad pnl--interactive lp-gauge" delay={0.08}>
            <span className="lk-chart__meta">Verified within SLA</span>
            <div className="lp-gauge__ring">
              <svg viewBox="0 0 120 120" aria-hidden="true">
                <circle cx="60" cy="60" r="50" fill="none" stroke="var(--line)" strokeWidth="10" />
                <motion.circle cx="60" cy="60" r="50" fill="none" stroke="var(--ok)" strokeWidth="10" strokeLinecap="round" animate={{ strokeDasharray: `${Math.round(ds.sla * 314)} 314` }} transition={{ duration: 0.8, ease: EASE }} />
              </svg>
              <div>
                <strong className="display tnum">{Math.round(ds.sla * 100)}%</strong>
                <small>median {ds.hours}h</small>
              </div>
            </div>
            <Sparkline values={vals.slice(-14)} color="var(--ok)" height={40} />
          </Reveal>
          <Reveal className="pnl pnl--pad lp-bento__wide">
            <div className="lk-chart__head">
              <span className="lk-chart__meta">When exceptions arrive · day × hour</span>
              <span className="lk-chart__meta" style={{ color: "var(--escalation)" }}>■ hotspot</span>
            </div>
            <div className="lk-heat" style={{ gridTemplateColumns: "36px repeat(24, minmax(0, 1fr))" }} role="img" aria-label="Exceptions by day and hour">
              {heat.map((row, di) => (
                <HeatRow key={di} day={["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][di]} row={row} />
              ))}
            </div>
          </Reveal>
          <Reveal className="pnl pnl--pad lp-limit" delay={0.08}>
            <span className="lk-chart__meta">Daily limit · what-if</span>
            <label htmlFor="lp-limit">
              New refund <code>{money(amount)}</code>
            </label>
            <input id="lp-limit" type="range" min={0} max={90000} step={1000} value={amount} onChange={(e) => setAmount(Number(e.target.value))} />
            <div className="lp-limit__bar" aria-hidden="true">
              <i style={{ width: "44%", background: "var(--ok)" }} />
              <i style={{ width: "12%", background: "var(--provider)" }} />
              <i style={{ width: "8%", background: "var(--signal)" }} />
              <i style={{ width: `${Math.min(36, (amount / 200000) * 100)}%`, background: lim.allowed ? "var(--ok)" : "var(--escalation)", opacity: 0.7 }} />
            </div>
            <p className="lp-limit__msg" data-ok={lim.allowed}>
              {lim.allowed ? `Allowed · ${money(lim.after)} headroom after reservation` : `Blocked · over the daily limit by ${money(lim.over)} (completed + pending + reserved)`}
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

function HeatRow({ day, row }: { day: string; row: number[] }) {
  return (
    <>
      <span className="lk-axis" style={{ aspectRatio: "auto" }}>{day}</span>
      {row.map((v, h) => (
        <span key={h} title={`${day} ${h}:00`} style={{ background: v > 1.08 ? "var(--ember)" : `color-mix(in srgb, var(--signal) ${Math.round(6 + Math.min(1, v) * 80)}%, transparent)` }} />
      ))}
    </>
  );
}

const ROLES = [
  { title: "Customer", body: "Report a problem, follow the case, see when money is back.", features: ["Parcel-style refund tracker", "Assistant with cited answers", "Notification on every state"], kpis: [["Open cases", 2], ["On the way", 1], ["Resolved", 5]] },
  { title: "Merchant", body: "Watch exceptions, refunds and settlements for your store.", features: ["Settlement waterfall and cohorts", "Dispute evidence builder", "Team roles"], kpis: [["Exceptions", 7], ["Refunds", 4], ["Settlements", 3]] },
  { title: "Operator", body: "Work the queue, gather evidence, propose a resolution.", features: ["Keyboard-first queue with ⌘K", "Copilot drafts, you decide", "Case replay"], kpis: [["My queue", 12], ["Waiting", 3], ["Escalated", 1]] },
  { title: "Supervisor", body: "Approve exact proposals and watch the pipeline.", features: ["Hold-to-approve with payload diff", "Limit headroom at a glance", "Live command center"], kpis: [["To approve", 6], ["Approved", 9], ["Expired", 1]] },
  { title: "Risk", body: "Spot rings, place holds, tune thresholds safely.", features: ["Account link graph", "Threshold what-if simulator", "Hold management"], kpis: [["Flagged", 31], ["Holds", 4], ["Reviews", 12]] },
  { title: "Admin", body: "Manage tenants, teams, roles and policies.", features: ["Visual policy editor with backtest", "Role matrix", "Audit search"], kpis: [["Users", 48], ["Tenants", 3], ["Policies", 2]] },
] as const;

export function Portals() {
  const [r, setR] = useState(2);
  const role = ROLES[r];
  return (
    <section id="portals" className="lp-section">
      <div className="lp-wrap">
        <Reveal className="lp-head">
          <h2>Six portals, one login</h2>
          <div className="pill-tabs lp-roles" role="tablist" aria-label="Roles">
            {ROLES.map((x, i) => (
              <button key={x.title} type="button" role="tab" aria-selected={i === r} onClick={() => setR(i)}>
                {i === r && <motion.span layoutId="lp-role-pill" className="lp-roles__pill" transition={{ duration: 0.35, ease: EASE }} />}
                <span style={{ position: "relative" }}>{x.title}</span>
              </button>
            ))}
          </div>
        </Reveal>
        <div className="pnl lp-portal" role="tabpanel" aria-label={`${role.title} portal`}>
          <AnimatePresence mode="wait">
            <motion.div key={role.title} className="lp-portal__copy" initial={{ opacity: 0, y: 16, filter: "blur(6px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.35, ease: EASE }}>
              <span className="eyebrow eyebrow--signal tnum">0{r + 1} / 06</span>
              <h3>{role.title}</h3>
              <p>{role.body}</p>
              <ul>
                {role.features.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </motion.div>
          </AnimatePresence>
          <div className="lp-portal__mock">
            {role.kpis.map(([k, v], i) => (
              <div key={`${role.title}-${k}`} className="lp-portal__kpi rise-in" style={{ animationDelay: `${i * 60}ms` }}>
                <span>{k}</span>
                <strong className="display tnum">{v}</strong>
                <Sparkline values={Array.from({ length: 10 }, (_, j) => 8 + 8 * Math.sin(j / 1.6 + i + r))} color={["var(--signal)", "var(--ok)", "var(--escalation)"][i]} height={24} area={false} />
              </div>
            ))}
            <div className="lp-portal__bars" aria-hidden="true">
              {Array.from({ length: 20 }, (_, i) => {
                const v = 30 + 50 * Math.abs(Math.sin(i / 3 + r)) + (i % 4) * 5;
                return <i key={i} style={{ height: `${v}%`, background: i === 19 ? "var(--ok)" : `color-mix(in srgb, var(--signal) ${Math.round(25 + v / 2)}%, transparent)` }} />;
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Close({ dashboardHref }: { dashboardHref?: string | null }) {
  return (
    <>
      <section className="lp-close grid-bg">
        <Reveal>
          <h2>
            Watch the money <span style={{ color: "var(--ok)" }}>land.</span>
          </h2>
        </Reveal>
        <p>Every portal runs against the payment simulator. No real money, no real customer data.</p>
        <div className="lp-hero__cta" style={{ justifyContent: "center" }}>
          {dashboardHref ? (
            <Link href={dashboardHref} className="btn btn-lg btn-lime">Dashboard</Link>
          ) : (
            <Link href="/login" className="btn btn-lg btn-lime">Get started</Link>
          )}
          <a href="#simulator" className="btn btn-lg btn-glass">Run the simulator</a>
        </div>
      </section>
      <footer className="landing-footer lp-footer">
        <div className="landing-footer__cols">
          <p className="landing-legal">Synthetic data and simulator payment writes only. Not a licensed payment service.</p>
          <div>
            <p className="landing-footer__head">Product</p>
            <a href="#simulator">Simulator</a>
            <a href="#analytics">Analytics</a>
            <a href="#portals">Portals</a>
          </div>
          <div>
            <p className="landing-footer__head">Access</p>
            {dashboardHref ? <Link href={dashboardHref}>Dashboard</Link> : <Link href="/login">Log in</Link>}
            <Link href="/customer/login">Track a refund</Link>
          </div>
        </div>
        <FooterWordmark />
      </footer>
    </>
  );
}
