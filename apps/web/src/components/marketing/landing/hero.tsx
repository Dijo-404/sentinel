"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useScroll } from "framer-motion";
import { useRef } from "react";
import { LogoMark } from "@/components/brand/logo-mark";
import { MaskHeadline } from "@/components/motion/reveal";
import { ThemeToggle } from "@/components/motion/theme-toggle";
import { useWebGL } from "@/components/three/use-webgl";
import { formatMoney } from "@/components/ledger/money";
import { NumberRoll } from "@/components/ledger/number-roll";
import { Sankey } from "@/components/ledger/sankey";
import { useTicker } from "@/components/ledger/use-ticker";

const LedgerVault = dynamic(() => import("@/components/three/ledger-vault"), { ssr: false });

/** The product settles in INR (domain Payment/Refund currency). */
export const DEMO_CURRENCY = "INR";

const FEED = [
  ["rfnd_••7Q2K", "credit verified", "verified"],
  ["case_••91A", "evidence attached", ""],
  ["disp_••0F3", "approved · digest bound", "pending"],
  ["rfnd_••2MX", "provider pending", "reserved"],
  ["case_••7DE", "escalated to risk", "risk"],
  ["rfnd_••A13", "credit verified", "verified"],
  ["case_••4C2", "proposal drafted", ""],
] as const;

export function LandingNav({ dashboardHref }: { dashboardHref?: string | null }) {
  const t = useTicker(1600);
  return (
    <nav className="lp-nav" aria-label="Main">
      <div className="lp-nav__bar">
        <Link href="/" className="landing-wordmark">
          <LogoMark />
          Sentinel
        </Link>
        <span className="lp-nav__live">
          <span className="live-dot" aria-hidden="true" />
          <span className="tnum">{(1284 + t * 3).toLocaleString("en-US")}</span> cases settled today
          · simulated
        </span>
        <div className="lp-nav__links">
          <a href="#simulator">Simulator</a>
          <a href="#guardrails">Guardrails</a>
          <a href="#analytics">Analytics</a>
          <a href="#portals">Portals</a>
        </div>
        <div className="lp-nav__actions">
          <ThemeToggle />
          {dashboardHref ? (
            <Link href={dashboardHref} className="btn btn-primary" data-testid="landing-dashboard">
              Dashboard
            </Link>
          ) : (
            <Link href="/login" className="btn btn-primary">
              Get started
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}

export function Hero({ dashboardHref }: { dashboardHref?: string | null }) {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const webgl = useWebGL();
  const t = useTicker(1600);
  const feed = [0, 1, 2, 3].map((k) => FEED[(t + FEED.length * 4 - k) % FEED.length]);

  return (
    <header ref={ref} className="lp-hero grid-bg">
      {webgl ? (
        <LedgerVault progress={scrollYProgress} />
      ) : (
        <div className="ledger-vault ledger-vault--css" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
        </div>
      )}
      <div className="lp-hero__inner">
        <div className="lp-hero__copy">
          <p className="lp-badge">Payment exceptions, from evidence to outcome</p>
          <MaskHeadline
            className="lp-hero__title"
            text="Every refund, from complaint to confirmed credit."
          />
          <p className="lp-hero__lead">
            Investigate payment exceptions, review the exact proposed action, and track the verified
            outcome. Keep your team in control of every financial decision.
          </p>
          <div className="lp-hero__cta">
            {dashboardHref ? (
              <Link href={dashboardHref} className="btn btn-lg btn-lime">
                Open your dashboard
              </Link>
            ) : (
              <Link href="/login" className="btn btn-lg btn-lime">
                Get started
              </Link>
            )}
            <a href="#simulator" className="btn btn-lg btn-glass">
              Try the simulator
            </a>
          </div>
          <dl className="lp-hero__facts">
            <div>
              <dt>verified credit today (sim)</dt>
              <dd>
                <NumberRoll
                  value={formatMoney(1849200000 + t * 1370000, DEMO_CURRENCY).replace(/\.\d+$/, "")}
                />
              </dd>
            </div>
            <div>
              <dt>duplicate refund IDs on retry</dt>
              <dd className="tnum">0</dd>
            </div>
            <div>
              <dt>financial audit, unsampled</dt>
              <dd className="tnum">100%</dd>
            </div>
          </dl>
        </div>

        <div className="pnl lp-console" aria-label="Live money flow, simulated">
          <div className="lp-console__scan" aria-hidden="true" />
          <div className="lp-console__head">
            <span className="eyebrow">Live money flow · last 60 min</span>
            <span className="status" data-tone="verified">
              simulator
            </span>
          </div>
          <Sankey
            label="Cases flowing from intake through approval to verified credit"
            width={560}
            height={220}
            nodes={[
              { id: "rf", label: "Refunds", column: 0, color: "var(--signal)" },
              { id: "di", label: "Disputes", column: 0, color: "var(--tide)" },
              { id: "du", label: "Duplicates", column: 0, color: "var(--orchid)" },
              { id: "ap", label: "Approved", column: 1, color: "var(--mist)" },
              { id: "es", label: "Escalated", column: 1, color: "var(--ember)" },
              { id: "ve", label: "Verified", column: 2, color: "var(--verified)" },
              { id: "pe", label: "Pending", column: 2, color: "var(--tide)" },
            ]}
            links={[
              { source: "rf", target: "ap", value: 214 + t, color: "var(--signal)" },
              { source: "di", target: "ap", value: 86, color: "var(--tide)" },
              { source: "di", target: "es", value: 14, color: "var(--ember)" },
              { source: "du", target: "ap", value: 64, color: "var(--orchid)" },
              { source: "ap", target: "ve", value: 318 + t, color: "var(--verified)" },
              { source: "ap", target: "pe", value: 46, color: "var(--tide)" },
            ]}
          />
          <ul className="lp-console__feed" aria-live="polite">
            {feed.map(([ref, msg, tone], k) => (
              <li key={`${t}-${k}`} className={k === 0 ? "feed-in" : undefined}>
                <span className="status" data-tone={tone || undefined}>
                  {msg}
                </span>
                <code>{ref}</code>
                <span className="lp-console__ago">{k === 0 ? "now" : `${k * 2}s`}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </header>
  );
}
