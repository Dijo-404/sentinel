/**
 * Gated FinHarness / FinBench admin projection (roles.md M5/M8).
 * Never invents live scores — mirrors packages/telemetry project_admin_observability_health.
 */

export type FinGate = "gated_disabled" | "shadow_read_only_unavailable";

export type AdminFinGates = {
  finharness: FinGate;
  finbench: FinGate;
  live_stats: null;
  notes: string[];
};

export function projectAdminFinGates(
  env: Record<string, string | undefined> = process.env as Record<string, string | undefined>,
): AdminFinGates {
  const finharnessEnabled = env.FINHARNESS_ADMIN_ENABLED === "true";
  const finbenchEnabled = env.FINBENCH_ADMIN_ENABLED === "true";
  return {
    finharness: finharnessEnabled ? "shadow_read_only_unavailable" : "gated_disabled",
    finbench: finbenchEnabled ? "shadow_read_only_unavailable" : "gated_disabled",
    live_stats: null,
    notes: [
      "FinHarness/FinBench remain independently gated (roles.md M5/M8); not claimed complete.",
      "live_stats is always null — no fake live rates or benchmark scores.",
      "Enable FINHARNESS_ADMIN_ENABLED / FINBENCH_ADMIN_ENABLED only when peers are assembled.",
    ],
  };
}
