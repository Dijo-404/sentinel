"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { HeroStage } from "./hero-stage";

type Props = {
  dashboardHref?: string | null;
};

const FEATURES = [
  {
    title: "Investigate",
    body: "Scoped evidence and timelines without exposing raw payment identifiers.",
  },
  {
    title: "Approve",
    body: "Digest-bound supervisor decisions — exact payload, no client edits.",
  },
  {
    title: "Dispatch",
    body: "Provider writes stay on the authoritative path with stable references.",
  },
  {
    title: "Verify",
    body: "Resolution only after postconditions pass. Pending is not credit.",
  },
] as const;

const STATS = [
  { label: "Roles", value: "6" },
  { label: "Ops stages", value: "4" },
  { label: "Fixture demos", value: "Ready" },
  { label: "Live money", value: "Never here" },
] as const;

export function LandingPage({ dashboardHref }: Props) {
  const reduceMotion = useReducedMotion();
  const fade = reduceMotion
    ? { initial: false, animate: { opacity: 1 } }
    : {
        initial: { opacity: 0, y: 16 },
        animate: { opacity: 1, y: 0 },
      };

  return (
    <div className="landing" data-testid="landing-page">
      <header className="landing-nav">
        <Link href="/" className="landing-wordmark">
          Sentinel
        </Link>
        <nav className="landing-nav__links" aria-label="Landing">
          <a href="#features">Features</a>
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

      <motion.section
        className="landing-hero"
        {...fade}
        transition={reduceMotion ? undefined : { duration: 0.45, ease: "easeOut" }}
      >
        <div className="landing-hero__copy">
          <h1>
            Payment ops from investigate to approve, dispatch, and verify
          </h1>
          <p className="landing-lead">
            Sentinel keeps models advisory and money paths server-owned — so
            queues, approvals, and outcomes stay auditable.
          </p>
          <div className="landing-hero__cta">
            {dashboardHref ? (
              <Link href={dashboardHref} className="btn btn-primary">
                Open dashboard
              </Link>
            ) : (
              <Link href="/login" className="btn btn-primary">
                Get started
              </Link>
            )}
            <a href="#how-it-works" className="btn btn-glass">
              How it works
            </a>
          </div>
        </div>
        <HeroStage />
      </motion.section>

      <section className="landing-stats" aria-label="Product facts">
        {STATS.map((s) => (
          <div key={s.label} className="landing-stat">
            <strong>{s.value}</strong>
            <span>{s.label}</span>
          </div>
        ))}
      </section>

      <section id="features" className="landing-bento">
        <h2>Built for payment exception work</h2>
        <p className="landing-section-lead">
          Night chrome, light canvases, and role portals that respect financial
          hard lines.
        </p>
        <div className="landing-bento__grid">
          {FEATURES.map((f) => (
            <article key={f.title} className="landing-card">
              <h3>{f.title}</h3>
              <p>{f.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="how-it-works" className="landing-quote">
        <blockquote>
          Models propose. Authenticated identity, deterministic policy, and
          verified outcomes govern money.
        </blockquote>
      </section>

      <section id="roles" className="landing-close">
        <h2>Six role portals, one shared login</h2>
        <p className="landing-section-lead">
          Customer, merchant, operator, supervisor, risk, and admin — workspace
          is authorized server-side.
        </p>
        {!dashboardHref ? (
          <Link href="/login" className="btn btn-primary">
            Get started
          </Link>
        ) : (
          <Link href={dashboardHref} className="btn btn-primary">
            Continue to dashboard
          </Link>
        )}
      </section>

      <footer className="landing-footer">
        <div>
          <p className="landing-wordmark">Sentinel</p>
          <p className="muted">Fixture demos only — not live production money.</p>
        </div>
        <div>
          <p>Product</p>
          <a href="#features">Features</a>
          <a href="#how-it-works">How it works</a>
          {dashboardHref ? (
            <Link href={dashboardHref}>Dashboard</Link>
          ) : (
            <Link href="/login">Log in</Link>
          )}
        </div>
        <div>
          <p>Legacy</p>
          <Link href="/intake">/intake</Link>
          <Link href="/ops">/ops</Link>
        </div>
      </footer>
    </div>
  );
}
