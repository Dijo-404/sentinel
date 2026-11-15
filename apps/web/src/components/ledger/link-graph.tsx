"use client";

export type GraphNode = { id: string; label: string; x: number; y: number; kind: "account" | "device" | "route"; score: number };
export type GraphEdge = { a: string; b: string; type: "device" | "route" | "behaviour" };

const EDGE_COLOR: Record<GraphEdge["type"], string> = {
  device: "var(--orchid)",
  route: "var(--ember)",
  behaviour: "var(--signal)",
};

/** Neighbour set of a node over the given edges (includes itself). Pure. */
export function neighbours(id: string, edges: GraphEdge[]): Set<string> {
  const out = new Set([id]);
  for (const e of edges) {
    if (e.a === id) out.add(e.b);
    if (e.b === id) out.add(e.a);
  }
  return out;
}

type Props = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selected: string;
  threshold: number;
  onSelect: (id: string) => void;
  width?: number;
  height?: number;
};

/** Account link graph. Every node is a focusable button (Enter/Space selects); high-risk accounts pulse. */
export function LinkGraph({ nodes, edges, selected, threshold, onSelect, width = 760, height = 460 }: Props) {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const nb = neighbours(selected, edges);
  const color = (n: GraphNode) =>
    n.kind !== "account" ? "var(--fog)" : n.score >= threshold ? "var(--ember)" : n.score > 0.3 ? "var(--signal)" : "var(--tide)";

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" className="lk-graph" role="group" aria-label="Linked accounts graph">
      {edges.map((e, i) => {
        const a = byId.get(e.a)!;
        const b = byId.get(e.b)!;
        const on = e.a === selected || e.b === selected;
        return (
          <g key={i}>
            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={EDGE_COLOR[e.type]} strokeWidth={on ? 2 : 1} opacity={on ? 0.9 : 0.2} />
            {on && <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={EDGE_COLOR[e.type]} strokeWidth={1.5} className="flow-dash" />}
          </g>
        );
      })}
      {nodes.map((n) => {
        const on = n.id === selected;
        const acct = n.kind === "account";
        const c = color(n);
        const hot = acct && n.score >= threshold;
        return (
          <g
            key={n.id}
            role="button"
            tabIndex={0}
            aria-pressed={on}
            aria-label={`${n.label}${acct ? `, risk ${n.score.toFixed(2)}` : `, shared ${n.kind}`}`}
            opacity={nb.has(n.id) ? 1 : 0.45}
            onClick={() => onSelect(n.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(n.id);
              }
            }}
          >
            {hot && <circle className="lk-graph__ping" cx={n.x} cy={n.y} r={14} fill="none" stroke="var(--ember)" strokeWidth={1.5} />}
            <circle cx={n.x} cy={n.y} r={acct ? (on ? 15 : 11) : 8} fill={on ? c : "var(--surface)"} stroke={c} strokeWidth={on ? 3 : 2} />
            <text x={n.x} y={n.y + (acct ? 28 : 24)} textAnchor="middle" fontFamily="var(--mono)" fontSize={10} fill={nb.has(n.id) ? "var(--ink-secondary)" : "var(--fog)"}>
              {n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
