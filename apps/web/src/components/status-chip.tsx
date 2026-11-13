import type { StatusLabel } from "@/domain/status-labels";

export function StatusChip({ label }: { label: StatusLabel }) {
  return (
    <span className="chip" data-kind={label.kind} data-testid="status-chip">
      {label.text}
    </span>
  );
}
