"use client";

import { useId } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartTooltip } from "./chart-tooltip";

export type AreaSeries = { key: string; name: string; color: string };

type Props = {
  data: Record<string, string | number>[];
  xKey: string;
  series: AreaSeries[];
  height?: number;
  /** Formats y-axis ticks and tooltip values, e.g. currency. */
  yFormat?: (v: number) => string;
};

/** Smoothed multi-series area chart with gradient fills and a shared tooltip. */
export function AreaTrend({
  data,
  xKey,
  series,
  height = 300,
  yFormat,
}: Props) {
  const uid = useId().replace(/:/g, "");
  return (
    <div className="area-trend" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 8, right: 8, left: -12, bottom: 0 }}
        >
          <defs>
            {series.map((s) => (
              <linearGradient
                key={s.key}
                id={`${uid}-${s.key}`}
                x1="0"
                x2="0"
                y1="0"
                y2="1"
              >
                <stop offset="0%" stopColor={s.color} stopOpacity={0.32} />
                <stop offset="100%" stopColor={s.color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid stroke="var(--lavender)" vertical={false} />
          <XAxis
            dataKey={xKey}
            tick={{ fill: "var(--ink-secondary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={yFormat}
            tick={{ fill: "var(--ink-secondary)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={52}
          />
          <Tooltip
            content={<ChartTooltip format={yFormat} />}
            cursor={{ stroke: "var(--periwinkle)", strokeDasharray: "4 4" }}
          />
          {series.map((s) => (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.name}
              stroke={s.color}
              strokeWidth={2}
              fill={`url(#${uid}-${s.key})`}
              activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface)" }}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
