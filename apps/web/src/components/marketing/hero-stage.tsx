"use client";

import dynamic from "next/dynamic";
import { useReducedMotion } from "framer-motion";
import { useWebGL } from "@/components/three/use-webgl";

const HeroScene = dynamic(() => import("@/components/three/hero-scene"), {
  ssr: false,
});

/** Ordered stages a case passes through; counts are simulator values. */
export const PIPELINE = [
  {
    key: "investigate",
    label: "Investigate",
    count: 24,
    body: "Evidence and timeline gathered, identifiers masked.",
  },
  {
    key: "approve",
    label: "Approve",
    count: 6,
    body: "A supervisor signs the exact amount and destination.",
  },
  {
    key: "dispatch",
    label: "Dispatch",
    count: 5,
    body: "One provider write per refund, with a stable reference.",
  },
  {
    key: "verify",
    label: "Verify",
    count: 18,
    body: "Closed only after the provider confirms the credit landed.",
  },
] as const;

/** WebGL orbit of the four stages behind the hero; a static glow without WebGL. */
export function HeroStage({ active }: { active: number }) {
  const webgl = useWebGL();
  const reduced = Boolean(useReducedMotion());
  return (
    <div className="hero-backdrop" aria-hidden="true">
      <div className="hero-backdrop__glow" />
      {webgl ? (
        <HeroScene
          stages={PIPELINE.map((s) => ({ key: s.key, count: s.count }))}
          active={active}
          reduced={reduced}
        />
      ) : null}
    </div>
  );
}
