"use client";

import { motion, useScroll, useSpring, useTransform } from "framer-motion";
import { useRef } from "react";
import { AreaTrend } from "@/components/viz/area-trend";
import { fixtureSeries } from "@/components/viz/fixture-series";
import { Legend } from "@/components/viz/legend";
import { PipelineFunnel } from "@/components/viz/pipeline-funnel";
import { FIXTURE_DOLLARS_PER_POINT, usdCompact } from "@/components/viz/format";
import { Sparkline } from "@/components/viz/sparkline";

const DAY = FIXTURE_DOLLARS_PER_POINT;

const CASES = [
  {
    id: "case_••••81f0",
    what: "Duplicate charge",
    amount: "$42.00",
    status: "Waiting approval",
    kind: "pending",
  },
  {
    id: "case_••••2c19",
    what: "Refund not credited",
    amount: "$129.90",
    status: "Provider pending",
    kind: "provider",
  },
  {
    id: "case_••••d4a7",
    what: "Item not received",
    amount: "$64.50",
    status: "Credit confirmed",
    kind: "credit",
  },
] as const;

/** Simulated merchant dashboard in an app frame; it straightens as it scrolls into view. */
export function ProductPreview() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "start 0.3"],
  });
  const progress = useSpring(scrollYProgress, {
    stiffness: 120,
    damping: 26,
    mass: 0.4,
  });
  const rotateX = useTransform(progress, [0, 1], [26, 0]);
  const scale = useTransform(progress, [0, 1], [0.88, 1]);
  const y = useTransform(progress, [0, 1], [80, 0]);

  const labels = fixtureSeries.dateLabels(14);
  const { volume, refundRequests } = fixtureSeries.volumeVsRefunds(14);
  const data = labels.map((day, i) => ({
    day,
    volume: (volume[i]?.y ?? 0) * DAY,
    refunds: (refundRequests[i]?.y ?? 0) * DAY,
  }));

  return (
    <div className="preview" ref={ref}>
      <motion.div className="preview__frame" style={{ rotateX, scale, y }}>
        <div className="preview__bar">
          <span className="preview__crumb">Merchant overview</span>
          <span className="preview__pill">Simulated data</span>
        </div>
        <div className="preview__body">
          <div className="preview__kpis">
            {[
              {
                label: "Captured volume",
                value: "$128,400",
                seed: 11,
                base: 220,
              },
              { label: "Open exceptions", value: "7", seed: 3, base: 8 },
              { label: "Refunds pending", value: "4", seed: 29, base: 18 },
              { label: "Verified this week", value: "18", seed: 41, base: 14 },
            ].map((k) => (
              <div key={k.label} className="preview__kpi">
                <span className="preview__kpi-label">{k.label}</span>
                <strong className="tnum">{k.value}</strong>
                <Sparkline
                  values={fixtureSeries.dailySeries(14, k.seed, k.base)}
                  width={160}
                  height={30}
                />
              </div>
            ))}
          </div>
          <div className="preview__chart">
            <div className="preview__chart-head">
              <span>Daily captured volume vs refund requests</span>
              <Legend
                items={[
                  { name: "Captured volume", color: "var(--viz-1)" },
                  { name: "Refund requests (value)", color: "var(--viz-2)" },
                ]}
              />
            </div>
            <AreaTrend
              data={data}
              xKey="day"
              height={210}
              yFormat={usdCompact}
              series={[
                {
                  key: "volume",
                  name: "Captured volume",
                  color: "var(--viz-1)",
                },
                {
                  key: "refunds",
                  name: "Refund requests (value)",
                  color: "var(--viz-2)",
                },
              ]}
            />
          </div>
          <div className="preview__pipeline">
            <span className="preview__section-title">Pipeline</span>
            <PipelineFunnel
              stages={[
                { key: "inv", label: "Investigating", count: 24 },
                { key: "app", label: "Waiting approval", count: 6 },
                { key: "dis", label: "Dispatching", count: 5 },
                { key: "ver", label: "Verified", count: 18 },
              ]}
              highlight="app"
            />
          </div>
          <div className="preview__cases">
            <span className="preview__section-title">Recent cases</span>
            <ul>
              {CASES.map((c) => (
                <li key={c.id}>
                  <span className="mono">{c.id}</span>
                  <span>{c.what}</span>
                  <span className="tnum">{c.amount}</span>
                  <span className="chip" data-kind={c.kind}>
                    {c.status}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
