"use client";

import { FixtureBanner } from "@/components/viz/fixture-banner";
import { UiState } from "@/components/ui-states";
import type { AuthSession } from "@/lib/server/auth";
import { PORTAL_META } from "@/lib/permissions";

type Props = {
  session: AuthSession;
  /**
   * Merchant settlement/analytics projections are not on case-api.
   * Until a merchant BFF exists, metrics stay unavailable (no fake numbers).
   */
  metricsAvailable?: boolean;
};

/**
 * Merchant dashboard: no synthetic volume/refund KPIs presented as live data.
 * Fixture banner labels the portal; metrics panel is explicit unavailable.
 */
export function MerchantOverview({
  session,
  metricsAvailable = false,
}: Props) {
  const meta = PORTAL_META.merchant;

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

      {metricsAvailable ? null : (
        <UiState
          tone="empty"
          title="Merchant metrics unavailable"
          detail="No scoped merchant projection API is wired in this shell. Charts and KPIs are withheld — not synthetic stand-ins for live volume, exceptions, or settlements."
        />
      )}
    </div>
  );
}
