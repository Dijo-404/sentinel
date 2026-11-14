"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/components/viz/chart-card";
import { FixtureBanner } from "@/components/viz/fixture-banner";
import { fixtureSeries } from "@/components/viz/fixture-series";
import { StatBlock } from "@/components/viz/stat-block";
import { TrendPill } from "@/components/viz/trend-pill";
import type { AuthSession } from "@/lib/server/auth";
import { PORTAL_META } from "@/lib/permissions";

type Props = {
  session: AuthSession;
};

const RECENT_EXCEPTIONS = [
  { id: "exc_••••a3f2", txn: "txn_••••91bc", status: "Open", age: "2h" },
  { id: "exc_••••c8e1", txn: "txn_••••44d0", status: "Open", age: "5h" },
  {
    id: "exc_••••12ab",
    txn: "txn_••••7f9e",
    status: "Investigating",
    age: "1d",
  },
] as const;

const SIMULATOR_CAPTION = "Simulator";

export function MerchantOverview({ session }: Props) {
  const meta = PORTAL_META.merchant;
  const { volume, refundRequests } = fixtureSeries.volumeVsRefunds(14);
  const chartData = volume.map((point, i) => ({
    day: point.x,
    volume: point.y,
    refundRequests: refundRequests[i]?.y ?? 0,
  }));

  return (
    <div className="stack" data-testid="merchant-dashboard">
      <div className="panel stack">
        <h1>{meta.title} dashboard</h1>
        <p className="muted">{meta.description}</p>
        <p className="muted">
          Signed in as {session.user.email} · {session.assignment.label}
        </p>
        <FixtureBanner />
      </div>

      <div
        className="stack"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(11rem, 1fr))",
          gap: "0.85rem",
        }}
      >
        <StatBlock
          label="Captured volume"
          value="$128,400"
          caption={SIMULATOR_CAPTION}
        />
        <StatBlock
          label="Open exceptions"
          value="7"
          caption={SIMULATOR_CAPTION}
        />
        <StatBlock
          label="Pending refund requests"
          value="4"
          caption={SIMULATOR_CAPTION}
        />
        <StatBlock
          label="Settlement status"
          value="On track"
          caption={SIMULATOR_CAPTION}
        />
      </div>

      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <TrendPill value="3.1% volume" direction="up" />
        <TrendPill value="1 refund req" direction="flat" />
      </div>

      <ChartCard title="Volume vs refund requests (simulator)">
        <div style={{ width: "100%", height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
            >
              <CartesianGrid
                stroke="rgba(195,195,204,0.25)"
                strokeDasharray="3 3"
              />
              <XAxis dataKey="day" tick={{ fill: "#c3c3cc", fontSize: 11 }} />
              <YAxis tick={{ fill: "#c3c3cc", fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Area
                type="monotone"
                dataKey="volume"
                name="Volume"
                stroke="#5266eb"
                fill="#9cb4e8"
                fillOpacity={0.35}
              />
              <Area
                type="monotone"
                dataKey="refundRequests"
                name="Refund requests"
                stroke="#c3c3cc"
                fill="#edecfb"
                fillOpacity={0.45}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <div className="panel stack">
        <h2>Recent exceptions</h2>
        <p className="muted">
          Simulator stubs — masked synthetic ids; advisory only.
        </p>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "0.9rem",
          }}
        >
          <thead>
            <tr>
              <th align="left">Exception</th>
              <th align="left">Transaction</th>
              <th align="left">Status</th>
              <th align="left">Age</th>
            </tr>
          </thead>
          <tbody>
            {RECENT_EXCEPTIONS.map((row) => (
              <tr key={row.id}>
                <td>{row.id}</td>
                <td>{row.txn}</td>
                <td>{row.status}</td>
                <td>{row.age}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
