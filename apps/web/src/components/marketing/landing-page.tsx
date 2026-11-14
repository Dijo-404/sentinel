"use client";

import Link from "next/link";
import {
  AnimatePresence,
  MotionConfig,
  motion,
  useMotionValueEvent,
  useScroll,
  useSpring,
} from "framer-motion";
import { useRef, useState, type ReactNode } from "react";
import { LogoMark } from "@/components/brand/logo-mark";
import { CountUp } from "@/components/motion/count-up";
import { Bars3D } from "@/components/viz/bars-3d";
import { fixtureSeries } from "@/components/viz/fixture-series";
import { RadialGauge } from "@/components/viz/radial-gauge";
import { Sparkline } from "@/components/viz/sparkline";
import { FooterWordmark } from "./footer-wordmark";
import { HeroStage, PIPELINE } from "./hero-stage";
import { ProductPreview } from "./product-preview";

type Props = {
  dashboardHref?: string | null;
};

const EASE = [0.22, 1, 0.36, 1] as const;
const HEADLINE = "Every refund, from complaint to confirmed credit";
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const DATASETS = [
  {
    key: "refunds",
    label: "Refund requests",
    seed: 29,
    base: 40,
    sla: 0.94,
    hours: 31,
  },
  {
    key: "disputes",
    label: "Disputes",
    seed: 11,
    base: 18,
    sla: 0.88,
    hours: 44,
  },
  {
    key: "duplicates",
    label: "Duplicate charges",
    seed: 5,
    base: 12,
    sla: 0.97,
    hours: 19,
  },
] as const;

const STEPS = [
  {
    title: "Investigate",
    body: "Operators see the case timeline and evidence. Card numbers and account identifiers stay masked.",
    checks: [
      "Order bound to the customer",
      "Fresh evidence attached",
      "Payment route recorded",
    ],
  },
  {
    title: "Approve",
    body: "A supervisor approves one exact proposal. Changing the amount or destination voids the approval.",
    checks: [
      "Digest of the exact payload",
      "Approval expires",
      "Limits include pending and reserved",
    ],
  },
  {
    title: "Dispatch",
    body: "Only the dispatcher writes to the payment provider, once, under a stable reference.",
    checks: [
      "Reservation held in one transaction",
      "No new refund ID on retry",
      "Timeouts reconcile, never re-send",
    ],
  },
  {
    title: "Verify",
    body: "A case resolves when the provider confirms the credit. Pending is not proof.",
    checks: [
      "Postconditions pass",
      "Financial audit written",
      "Escalation is not resolution",
    ],
  },
] as const;

const ROLES = [
  {
    key: "customer",
    title: "Customer",
    body: "Report a problem, follow the case, see when money is back.",
    sees: [
      ["Open cases", 2],
      ["Refunds on the way", 1],
      ["Resolved this year", 5],
    ],
  },
  {
    key: "merchant",
    title: "Merchant",
    body: "Watch exceptions, refunds and settlements for your store.",
    sees: [
      ["Open exceptions", 7],
      ["Refund requests", 4],
      ["Settlements due", 3],
    ],
  },
  {
    key: "operator",
    title: "Operator",
    body: "Work the queue, gather evidence, propose a resolution.",
    sees: [
      ["In my queue", 12],
      ["Waiting on input", 3],
      ["Escalated", 1],
    ],
  },
  {
    key: "supervisor",
    title: "Supervisor",
    body: "Approve exact proposals and watch the pipeline.",
    sees: [
      ["Waiting approval", 6],
      ["Approved today", 9],
      ["Expired", 1],
    ],
  },
  {
    key: "risk",
    title: "Risk",
    body: "Spot patterns, place holds, review flagged transactions.",
    sees: [
      ["Flagged", 31],
      ["Active holds", 4],
      ["Reviews today", 12],
    ],
  },
  {
    key: "admin",
    title: "Admin",
    body: "Manage tenants, teams, roles and policies.",
    sees: [
      ["Active users", 48],
      ["Tenants", 3],
      ["Policy changes", 2],
    ],
  },
] as const;

const usd = (v: number) => `$${Math.round(v).toLocaleString("en-US")}`;

function Reveal({
  children,
  className,
  id,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <motion.section
      id={id}
      className={className}
      initial={{ opacity: 0, y: 32 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, ease: EASE }}
    >
      {children}
    </motion.section>
  );
}

function Headline() {
  return (
    <h1 className="hero__title" aria-label={HEADLINE}>
      {HEADLINE.split(" ").map((word, i) => (
        <span
          key={`${word}-${i}`}
          className="hero__word-mask"
          aria-hidden="true"
        >
          <motion.span
            className="hero__word"
            initial={{ y: "110%", opacity: 0 }}
            animate={{ y: "0%", opacity: 1 }}
            transition={{ duration: 0.9, delay: 0.15 + i * 0.06, ease: EASE }}
          >
            {word}
          </motion.span>
        </span>
      ))}
    </h1>
  );
}

/** Pinned walkthrough: scrolling advances the stage; tabs jump to a stage. */
function ScrollSteps() {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end end"],
  });
  const fill = useSpring(scrollYProgress, { stiffness: 140, damping: 28 });
  const [step, setStep] = useState(0);
  useMotionValueEvent(scrollYProgress, "change", (v) =>
    setStep(
      Math.min(STEPS.length - 1, Math.max(0, Math.floor(v * STEPS.length))),
    ),
  );

  function go(i: number) {
    const el = ref.current;
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY;
    const range = el.offsetHeight - window.innerHeight;
    window.scrollTo({
      top: top + (range * (i + 0.5)) / STEPS.length,
      behavior: "smooth",
    });
  }

  const current = STEPS[step] ?? STEPS[0];

  return (
    <section ref={ref} id="how-it-works" className="scroll-steps">
      <div className="scroll-steps__sticky">
        <div className="landing-section__head">
          <h2>How a case moves</h2>
          <p className="landing-section-lead">
            Each stage has checks the next one relies on. Keep scrolling, or
            pick a stage.
          </p>
        </div>
        <div className="steps">
          <div className="steps__rail">
            <div className="steps__track" aria-hidden="true">
              <motion.i style={{ scaleY: fill }} />
            </div>
            <ol className="steps__list">
              {STEPS.map((s, i) => (
                <li key={s.title}>
                  <button
                    type="button"
                    className="steps__tab"
                    aria-pressed={i === step}
                    onClick={() => go(i)}
                  >
                    <span className="steps__num tnum">{i + 1}</span>
                    <span className="steps__title">{s.title}</span>
                    <span className="steps__count tnum">
                      {PIPELINE[i]?.count} cases
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          </div>
          <div className="steps__panel">
            <AnimatePresence mode="wait">
              <motion.div
                key={step}
                initial={{ opacity: 0, y: 18, filter: "blur(6px)" }}
                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -12, filter: "blur(4px)" }}
                transition={{ duration: 0.35, ease: EASE }}
              >
                <p className="steps__kicker tnum">
                  Stage {step + 1} of {STEPS.length}
                </p>
                <h3>{current.title}</h3>
                <p>{current.body}</p>
                <ul className="checklist">
                  {current.checks.map((c, i) => (
                    <motion.li
                      key={c}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.12 + i * 0.07, duration: 0.3 }}
                    >
                      <svg
                        viewBox="0 0 16 16"
                        width="16"
                        height="16"
                        aria-hidden="true"
                      >
                        <path
                          d="M3.5 8.5l3 3 6-7"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.7"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      {c}
                    </motion.li>
                  ))}
                </ul>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}

export function LandingPage({ dashboardHref }: Props) {
  const [dataset, setDataset] =
    useState<(typeof DATASETS)[number]["key"]>("refunds");
  const [stage, setStage] = useState(1);
  const [role, setRole] = useState<(typeof ROLES)[number]["key"]>("operator");

  const ds = DATASETS.find((d) => d.key === dataset) ?? DATASETS[0];
  const weekly = fixtureSeries.dailySeries(7, ds.seed, ds.base);
  const trend = fixtureSeries.dailySeries(30, ds.seed + 3, ds.base * 4);
  const bars = DAYS.map((label, i) => ({ label, value: weekly[i] ?? 0 }));
  const currentRole = ROLES.find((r) => r.key === role) ?? ROLES[2];
  const currentStage = PIPELINE[stage] ?? PIPELINE[1];

  return (
    <MotionConfig reducedMotion="user">
      <div className="landing" data-testid="landing-page">
        <header className="landing-nav">
          <Link href="/" className="landing-wordmark">
            <LogoMark inverse size={28} />
            Sentinel
          </Link>
          <nav className="landing-nav__links" aria-label="Landing">
            <a href="#product">Product</a>
            <a href="#analytics">Analytics</a>
            <a href="#how-it-works">How it works</a>
            <a href="#roles">Roles</a>
          </nav>
          <div className="landing-nav__actions">
            {dashboardHref ? (
              <Link
                href={dashboardHref}
                className="btn btn-primary"
                data-testid="landing-dashboard"
              >
                Dashboard
              </Link>
            ) : (
              <>
                <Link href="/login" className="btn btn-glass">
                  Log in
                </Link>
                <Link href="/login" className="btn btn-primary">
                  Get started
                </Link>
              </>
            )}
          </div>
        </header>

        <section className="hero">
          <HeroStage active={stage} />
          <div className="hero__inner">
            <Headline />
            <motion.p
              className="hero__lead"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6, ease: EASE }}
            >
              Sentinel runs payment exceptions through four checked stages.
              Models suggest, people approve, and the server moves money and
              proves it arrived.
            </motion.p>
            <motion.div
              className="hero__cta"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.72, ease: EASE }}
            >
              {dashboardHref ? (
                <Link href={dashboardHref} className="btn btn-primary btn-lg">
                  Open dashboard
                </Link>
              ) : (
                <Link href="/login" className="btn btn-primary btn-lg">
                  Get started
                </Link>
              )}
              <a href="#how-it-works" className="btn btn-glass btn-lg">
                See how it works
              </a>
            </motion.div>
            <motion.div
              className="hero__stages"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.95 }}
            >
              <div
                className="hero__chips"
                role="group"
                aria-label="Pipeline stages"
              >
                {PIPELINE.map((s, i) => (
                  <button
                    key={s.key}
                    type="button"
                    className="hero__chip"
                    aria-pressed={i === stage}
                    onClick={() => setStage(i)}
                    onMouseEnter={() => setStage(i)}
                    onFocus={() => setStage(i)}
                  >
                    {i === stage ? (
                      <motion.span
                        layoutId="hero-chip"
                        className="hero__chip-pill"
                        transition={{
                          type: "spring",
                          stiffness: 380,
                          damping: 32,
                        }}
                      />
                    ) : null}
                    <span className="hero__chip-text">
                      {s.label}
                      <span className="hero__chip-count tnum">{s.count}</span>
                    </span>
                  </button>
                ))}
              </div>
              <AnimatePresence mode="wait">
                <motion.p
                  key={currentStage.key}
                  className="hero__caption"
                  aria-live="polite"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.22 }}
                >
                  {currentStage.body}
                </motion.p>
              </AnimatePresence>
            </motion.div>
          </div>
        </section>

        <section
          id="product"
          className="landing-product"
          aria-label="Product preview"
        >
          <ProductPreview />
        </section>

        <section className="landing-stats" aria-label="Product facts">
          <div className="landing-stat">
            <strong>
              <CountUp value={4} />
            </strong>
            <span>checked stages per case</span>
          </div>
          <div className="landing-stat">
            <strong>
              <CountUp value={6} />
            </strong>
            <span>role portals, one login</span>
          </div>
          <div className="landing-stat">
            <strong>
              <CountUp value={1} />
            </strong>
            <span>provider write per refund</span>
          </div>
          <div className="landing-stat">
            <strong>
              <CountUp value={0} />
            </strong>
            <span>cases closed on a pending refund</span>
          </div>
        </section>

        <Reveal id="analytics" className="landing-section">
          <div className="landing-section__head">
            <h2>See where exceptions pile up</h2>
            <p className="landing-section-lead">
              Volume by weekday, time to verified credit and the 30-day trend,
              for each exception type.
            </p>
          </div>

          <div className="segmented" role="tablist" aria-label="Exception type">
            {DATASETS.map((d) => (
              <button
                key={d.key}
                type="button"
                role="tab"
                aria-selected={d.key === dataset}
                className="segmented__item"
                onClick={() => setDataset(d.key)}
              >
                {d.key === dataset ? (
                  <motion.span
                    layoutId="seg-pill"
                    className="segmented__pill"
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                ) : null}
                <span className="segmented__text">{d.label}</span>
              </button>
            ))}
          </div>

          <div className="analytics-grid">
            <article className="feature-card-dark analytics-grid__main">
              <div className="card-head">
                <h3>{ds.label} this week</h3>
                <span className="card-tag">Simulator</span>
              </div>
              <Bars3D
                bars={bars}
                unit={ds.label.toLowerCase()}
                tone="night"
                height={400}
              />
            </article>
            <article className="feature-card-dark">
              <div className="card-head">
                <h3>Verified within SLA</h3>
                <span className="card-tag">30 days</span>
              </div>
              <div className="analytics-grid__gauge">
                <RadialGauge
                  key={ds.key}
                  value={ds.sla}
                  label="Credit confirmed in 48h"
                  caption={`Median ${ds.hours}h to credit`}
                />
              </div>
            </article>
            <article className="feature-card-dark">
              <div className="card-head">
                <h3>Refunded value</h3>
                <span className="card-tag">30 days</span>
              </div>
              <p className="analytics-grid__big tnum">
                <CountUp
                  key={ds.key}
                  value={trend.reduce((a, b) => a + b, 0) * 12}
                  format={usd}
                  duration={1}
                />
              </p>
              <Sparkline
                key={ds.key}
                values={trend}
                width={320}
                height={72}
                tone="periwinkle"
                label={`${ds.label}, 30-day trend`}
              />
            </article>
          </div>
        </Reveal>

        <ScrollSteps />

        <Reveal className="landing-section">
          <div className="guardrails">
            <article className="guardrails__col">
              <h3>What the model can do</h3>
              <ul>
                <li>Summarise evidence</li>
                <li>Suggest a resolution and amount</li>
                <li>Draft a reply to the customer</li>
              </ul>
            </article>
            <div className="guardrails__divider" aria-hidden="true" />
            <article className="guardrails__col guardrails__col--server">
              <h3>What only the server can do</h3>
              <ul>
                <li>Check identity, scope and limits</li>
                <li>Accept an exact supervisor approval</li>
                <li>Write to the payment provider</li>
                <li>Mark a case resolved</li>
              </ul>
            </article>
          </div>
        </Reveal>

        <Reveal id="roles" className="landing-section">
          <div className="landing-section__head">
            <h2>Six portals, one login</h2>
            <p className="landing-section-lead">
              Everyone signs in at the same place and lands in the workspace
              they are authorised for.
            </p>
          </div>
          <div className="roles">
            <div className="roles__tabs" role="tablist" aria-label="Roles">
              {ROLES.map((r) => (
                <button
                  key={r.key}
                  type="button"
                  role="tab"
                  aria-selected={r.key === role}
                  className="roles__tab"
                  onClick={() => setRole(r.key)}
                >
                  {r.key === role ? (
                    <motion.span
                      layoutId="role-pill"
                      className="roles__pill"
                      transition={{
                        type: "spring",
                        stiffness: 380,
                        damping: 32,
                      }}
                    />
                  ) : null}
                  <span className="roles__tab-text">{r.title}</span>
                </button>
              ))}
            </div>
            <AnimatePresence mode="wait">
              <motion.article
                key={currentRole.key}
                role="tabpanel"
                className="roles__panel"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.28, ease: EASE }}
              >
                <div>
                  <h3>{currentRole.title}</h3>
                  <p>{currentRole.body}</p>
                </div>
                <div className="roles__mock">
                  {currentRole.sees.map(([label, value]) => (
                    <div key={label} className="roles__mock-tile">
                      <span>{label}</span>
                      <strong className="tnum">{value}</strong>
                    </div>
                  ))}
                </div>
              </motion.article>
            </AnimatePresence>
          </div>
        </Reveal>

        <section className="landing-quote">
          <blockquote>
            Models propose. Authenticated identity, deterministic policy and
            verified outcomes govern money.
          </blockquote>
        </section>

        <section className="landing-close">
          <h2>Try it with simulated payments</h2>
          <p className="landing-section-lead">
            Sign in with a demo account for any of the six roles.
          </p>
          {dashboardHref ? (
            <Link href={dashboardHref} className="btn btn-primary btn-lg">
              Continue to dashboard
            </Link>
          ) : (
            <Link href="/login" className="btn btn-primary btn-lg">
              Get started
            </Link>
          )}
        </section>

        <footer className="landing-footer">
          <div className="landing-footer__cols">
            <div>
              <p className="landing-footer__head landing-footer__brand">
                <LogoMark inverse size={24} />
                Sentinel
              </p>
              <p className="landing-legal">
                Demo environment. All payments, customers and metrics shown are
                simulated. No real money moves.
              </p>
            </div>
            <div>
              <p className="landing-footer__head">Product</p>
              <a href="#analytics">Analytics</a>
              <a href="#how-it-works">How it works</a>
              {dashboardHref ? (
                <Link href={dashboardHref}>Dashboard</Link>
              ) : (
                <Link href="/login">Log in</Link>
              )}
            </div>
            <div>
              <p className="landing-footer__head">Legacy</p>
              <Link href="/intake">/intake</Link>
              <Link href="/ops">/ops</Link>
            </div>
          </div>
          <FooterWordmark />
        </footer>
      </div>
    </MotionConfig>
  );
}
