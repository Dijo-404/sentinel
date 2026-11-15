"use client";

import { MotionConfig } from "framer-motion";
import { SmoothScroll } from "@/components/motion/smooth-scroll";
import { Hero, LandingNav } from "./landing/hero";
import { Analytics, Close, Guardrails, Portals, Problem, Simulator, Ticker } from "./landing/sections";

type Props = {
  dashboardHref?: string | null;
};

/** Marketing page: one scroll timeline from complaint to confirmed credit. */
export function LandingPage({ dashboardHref }: Props) {
  return (
    <MotionConfig reducedMotion="user">
      <SmoothScroll />
      <div className="landing lp" data-testid="landing-page">
        <LandingNav dashboardHref={dashboardHref} />
        <main>
          <Hero dashboardHref={dashboardHref} />
          <Ticker />
          <Problem />
          <Simulator />
          <Guardrails />
          <Analytics />
          <Portals />
        </main>
        <Close dashboardHref={dashboardHref} />
      </div>
    </MotionConfig>
  );
}
