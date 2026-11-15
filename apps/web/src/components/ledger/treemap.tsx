"use client";

export type TreeItem = { label: string; value: number; color: string; display: string };

/** Flex treemap: area ∝ value via flex-grow. Click to select; selection drives a detail line. */
export function Treemap({ items, selected, onSelect }: { items: TreeItem[]; selected: number; onSelect: (i: number) => void }) {
  const total = items.reduce((a, b) => a + b.value, 0) || 1;
  return (
    <div className="lk-treemap">
      {items.map((it, i) => (
        <button
          key={it.label}
          type="button"
          aria-pressed={i === selected}
          onClick={() => onSelect(i)}
          style={{
            flexGrow: it.value,
            flexBasis: `${Math.max(14, (it.value / total) * 100)}%`,
            minHeight: 56 + Math.round((it.value / total) * 120),
            background: it.color,
          }}
        >
          <span>{it.label}</span>
          <small className="tnum">{it.display}</small>
        </button>
      ))}
    </div>
  );
}
