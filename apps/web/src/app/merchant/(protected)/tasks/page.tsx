"use client";

import { UiState } from "@/components/ui-states";

/**
 * SLA tasks belong on merchant-sla GET /v1/tasks.
 * Task-5 ruling: prefer merchant-inbox / case-api; inbox has exceptions list
 * only (no /v1/tasks). Fail closed — no invented rows.
 */
export default function MerchantTasksPage() {
  return (
    <div className="panel stack" data-testid="merchant-tasks">
      <h1>Tasks</h1>
      <p className="muted">
        SLA task list withheld. merchant-inbox has no tasks route; case-api has
        no merchant task list. Live rows not invented.
      </p>
      <div data-testid="peer-error">
        <UiState
          tone="error"
          title="Tasks list unavailable"
          detail="merchant-inbox exposes GET /v1/exceptions only. No GET /v1/tasks on preferred peers. merchant-sla has GET /v1/tasks (out of this page’s preferred peer set) — not wired here. Fail closed."
        />
      </div>
    </div>
  );
}
