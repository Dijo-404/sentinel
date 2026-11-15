"use client";

import { useId } from "react";

export type SankeyNode = { id: string; label: string; column: number; color: string };
export type SankeyLink = { source: string; target: string; value: number; color: string };

type Laid = {
  nodes: (SankeyNode & { x: number; y: number; h: number; value: number })[];
  links: (SankeyLink & { path: string; width: number })[];
};

/** Column layout: node height ∝ max(in, out); ribbons stack inside each node. Pure, testable. */
export function layoutSankey(
  nodes: SankeyNode[],
  links: SankeyLink[],
  { width, height, nodeWidth = 10, gap = 18 }: { width: number; height: number; nodeWidth?: number; gap?: number },
): Laid {
  const cols = Math.max(...nodes.map((n) => n.column)) + 1;
  const inflow = new Map<string, number>();
  const outflow = new Map<string, number>();
  for (const l of links) {
    outflow.set(l.source, (outflow.get(l.source) ?? 0) + l.value);
    inflow.set(l.target, (inflow.get(l.target) ?? 0) + l.value);
  }
  const value = (id: string) => Math.max(inflow.get(id) ?? 0, outflow.get(id) ?? 0);
  const colTotals = Array.from({ length: cols }, (_, c) =>
    nodes.filter((n) => n.column === c).reduce((a, n) => a + value(n.id), 0),
  );
  const colCounts = Array.from({ length: cols }, (_, c) => nodes.filter((n) => n.column === c).length);
  const scale = Math.min(...colTotals.map((t, c) => (height - gap * (colCounts[c] - 1)) / (t || 1)));

  const laid = new Map<string, Laid["nodes"][number]>();
  const cursor = Array(cols).fill(0) as number[];
  for (const n of nodes) {
    const h = Math.max(4, value(n.id) * scale);
    const x = cols === 1 ? 0 : (n.column / (cols - 1)) * (width - nodeWidth);
    laid.set(n.id, { ...n, x, y: cursor[n.column], h, value: value(n.id) });
    cursor[n.column] += h + gap;
  }
  const outOff = new Map<string, number>();
  const inOff = new Map<string, number>();
  const laidLinks = links.map((l) => {
    const s = laid.get(l.source)!;
    const t = laid.get(l.target)!;
    const w = l.value * scale;
    const sy = s.y + (outOff.get(s.id) ?? 0) + w / 2;
    const ty = t.y + (inOff.get(t.id) ?? 0) + w / 2;
    outOff.set(s.id, (outOff.get(s.id) ?? 0) + w);
    inOff.set(t.id, (inOff.get(t.id) ?? 0) + w);
    const x0 = s.x + nodeWidth;
    const x1 = t.x;
    const mx = (x0 + x1) / 2;
    return { ...l, width: w, path: `M${x0} ${sy.toFixed(1)} C ${mx} ${sy.toFixed(1)}, ${mx} ${ty.toFixed(1)}, ${x1} ${ty.toFixed(1)}` };
  });
  return { nodes: [...laid.values()], links: laidLinks };
}

type Props = {
  nodes: SankeyNode[];
  links: SankeyLink[];
  width?: number;
  height?: number;
  label: string;
  /** Particles per link (0 = static). */
  particles?: number;
  format?: (v: number) => string;
};

/** Animated money-flow ribbons with travelling particles. */
export function Sankey({ nodes, links, width = 900, height = 320, label, particles = 2, format = String }: Props) {
  const uid = useId().replace(/:/g, "");
  const laid = layoutSankey(nodes, links, { width, height });
  return (
    <svg viewBox={`-4 -24 ${width + 8} ${height + 40}`} width="100%" role="img" aria-label={label} className="lk-sankey">
      <g fill="none" strokeLinecap="butt">
        {laid.links.map((l, i) => (
          <path key={`r${i}`} id={`${uid}-l${i}`} d={l.path} stroke={l.color} strokeWidth={Math.max(1, l.width)} opacity={0.2} />
        ))}
        {laid.links.map((l, i) => (
          <path key={`f${i}`} d={l.path} stroke={l.color} strokeWidth={1.5} className="flow-dash" style={{ animationDuration: `${1 + (i % 3) * 0.4}s` }} />
        ))}
      </g>
      {laid.nodes.map((n) => (
        <g key={n.id}>
          <rect x={n.x} y={n.y} width={10} height={n.h} rx={3} fill={n.color} />
          <text
            x={n.column === 0 ? n.x + 16 : n.x - 6}
            y={n.y - 6}
            textAnchor={n.column === 0 ? "start" : "end"}
            fontFamily="var(--mono)"
            fontSize={11}
            fill="var(--ink-secondary)"
          >
            {`${n.label} ${format(n.value)}`}
          </text>
        </g>
      ))}
      {particles > 0 &&
        laid.links.flatMap((l, i) =>
          Array.from({ length: particles }, (_, p) => (
            <circle key={`p${i}-${p}`} r={3.5} fill={l.color} className="lk-particle">
              <animateMotion dur={`${2.6 + (i % 4) * 0.5}s`} begin={`${(p * 1.3).toFixed(1)}s`} repeatCount="indefinite">
                <mpath href={`#${uid}-l${i}`} />
              </animateMotion>
            </circle>
          )),
        )}
    </svg>
  );
}
